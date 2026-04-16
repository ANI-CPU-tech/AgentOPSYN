import json
import re
from typing import Optional
from .ollama_client import chat

# Threshold lowered as requested to ensure execution path is triggered
CONFIDENCE_THRESHOLD = 4.50
MAX_REPLAN_ATTEMPTS = 2

# List of known action types for the Executor to use
KNOWN_ACTIONS = [
    "flush_redis",
    "scale_deployment",
    "restart_service",
    "create_jira_ticket",
    "send_slack_alert",
    "execute_command",
]


def build_context_string(retrieval_results: list) -> str:
    """Format retrieved chunks into a clean context block for the prompt."""
    if not retrieval_results:
        return "No relevant context found."

    parts = []
    for i, result in enumerate(retrieval_results, 1):
        source = result.get("event_id") or result.get("runbook_id") or "unknown"
        parts.append(
            f"[Source {i} | id:{source} | similarity:{result['similarity']:.2f}]\n"
            f"{result['content']}"
        )
    return "\n\n---\n\n".join(parts)


def extract_json(text: str):
    """Robustly extracts and cleans JSON from LLM responses."""
    try:
        # Strip common LLM markdown and leading/trailing whitespace
        text = text.strip().strip("`").replace("json\n", "")
        # Remove single-line comments that local models often include
        text = re.sub(r"//.*", "", text)

        match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except Exception as e:
        print(f"DEBUG: JSON Extraction failed: {e}")
    return None


# ─────────────────────────────────────────────
# PLANNER
# ─────────────────────────────────────────────


def run_planner(query: str, context: str) -> list:
    messages = [
        {
            "role": "system",
            "content": (
                "You are OPSYN, an expert DevOps AI. "
                "CRITICAL RULE: If the user is only asking for a status, explanation, or summary, "
                "your steps MUST ONLY be observational (e.g., 'Read logs', 'Analyze metrics'). "
                "DO NOT plan any corrective actions (like restarting or flushing) unless the user explicitly requests a fix. "
                "Output ONLY a JSON array of strings."
            ),
        },
        {"role": "user", "content": f"Query: {query}\n\nContext:\n{context}"},
    ]
    response = chat(messages, temperature=0.1)
    steps = extract_json(response)
    if isinstance(steps, list):
        return [str(s) for s in steps]
    return [response]


# ─────────────────────────────────────────────
# EXECUTOR
# ─────────────────────────────────────────────


def run_executor(query: str, context: str, steps: list) -> dict:
    steps_str = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))

    # Instruction to force the LLM to use our expected schema
    # Instruction to force the LLM to use our expected schema
    action_guidance = (
        f"If an action is required, you MUST use one of these action_types: {KNOWN_ACTIONS}. "
        "CRITICAL: You must provide the correct keys in action_payload:\n"
        "- 'send_slack_alert' REQUIRES {'message': 'your detailed string'}\n"
        "- 'create_jira_ticket' REQUIRES {'summary': '...', 'description': '...'}\n"
        "- 'scale_deployment' REQUIRES {'service': '...', 'replicas': int}"
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are OPSYN, a DevOps reasoning engine. "
                "Review the plan and context to provide an answer. "
                f"{action_guidance}. "
                "Respond ONLY with a JSON object:\n"
                "- answer: string (detailed, with [Source N] citations)\n"
                "- action_type: string or null\n"
                "- action_payload: object or null (e.g. {'command': '...', 'service': '...'})\n"
                "- needs_approval: boolean (true for risky operations)"
            ),
        },
        {
            "role": "user",
            "content": f"Query: {query}\n\nPlan:\n{steps_str}\n\nContext:\n{context}",
        },
    ]

    response = chat(messages, temperature=0.2)
    result = extract_json(response)

    # --- THE CIRCUIT BREAKER ---
    # Words that usually imply a read-only question
    question_words = ["what", "how", "why", "when", "who", "summarize", "status"]
    query_lower = query.strip().lower()
    is_question = any(query_lower.startswith(word) for word in question_words)

    if result and isinstance(result, dict):
        action_type = result.get("action_type")
        needs_approval = result.get("needs_approval", False)
        action_payload = result.get("action_payload", {})

        # If it's just a question, forcefully neutralize any hallucinated actions
        if is_question:
            print(
                "DEBUG: Circuit Breaker Activated! Neutralizing action for read-only query."
            )
            action_type = None
            needs_approval = False
            action_payload = {}

        return {
            "answer": result.get("answer", "No description provided."),
            "action_type": action_type,
            "action_payload": action_payload,
            "needs_approval": needs_approval,
        }

    # Fallback if extraction fails completely
    return {
        "answer": response,
        "action_type": None,
        "action_payload": {},
        "needs_approval": False,
    }


# ─────────────────────────────────────────────
# VALIDATOR
# ─────────────────────────────────────────────


def run_validator(query: str, answer: str, steps: list) -> dict:
    messages = [
        {
            "role": "system",
            "content": "Validate the answer. Respond ONLY with JSON: {is_valid: bool, reason: str, needs_replan: bool}",
        },
        {
            "role": "user",
            "content": f"Query: {query}\n\nAnswer produced:\n{answer}",
        },
    ]
    response = chat(messages, temperature=0.0)
    result = extract_json(response)
    return result or {"is_valid": True, "reason": "", "needs_replan": False}


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────


def run_agent_pipeline(
    query: str, retrieval_results: list, org_id: str, query_log_id: str, user
) -> dict:
    context = build_context_string(retrieval_results)
    replan_count = 0
    steps = []
    execution_result = {}

    while replan_count <= MAX_REPLAN_ATTEMPTS:
        steps = run_planner(query, context)
        execution_result = run_executor(query, context, steps)
        validation = run_validator(query, execution_result["answer"], steps)

        if validation.get("is_valid") and not validation.get("needs_replan"):
            break
        replan_count += 1

    # 4. SAFETY AND PERSISTENCE LOGIC
    action_type = execution_result.get("action_type")
    action_payload = execution_result.get("action_payload") or {}

    should_require_approval = False
    pending_action_id = None

    # ONLY check safety and save to DB if an action actually exists
    if action_type:
        # Import safety modules locally to avoid circular dependencies
        from approvals.safety import classify_risk

        # Local Safety Check: Secondary validation of the LLM's risk assessment
        safety_info = classify_risk(action_type, action_payload)

        # Logic: Require approval if LLM says so OR if our safety matrix says it's risky
        should_require_approval = execution_result.get(
            "needs_approval"
        ) or safety_info.get("needs_approval", False)

        if should_require_approval:
            print(
                f"DEBUG: Triggering creation for {action_type} (Approval Required: {should_require_approval})"
            )
            pending_action_id = _create_pending_action(
                action_type=action_type,
                action_payload=action_payload,
                query_log_id=query_log_id,
                user=user,
                org_id=org_id,
            )

    return {
        "answer": execution_result.get("answer", ""),
        "steps": steps,
        "action_type": action_type,
        "needs_approval": should_require_approval,
        "pending_action_id": pending_action_id,
        "replan_count": replan_count,
    }


def _create_pending_action(
    action_type: str, action_payload: dict, query_log_id: str, user, org_id: str
) -> Optional[str]:
    """Saves the suggested action to the database for human review."""
    try:
        from approvals.models import AgentAction
        from approvals.safety import classify_risk
        from accounts.models import Organization

        org = Organization.objects.get(id=org_id)

        # Get standardized risk metadata
        safety_info = classify_risk(action_type, action_payload)

        action = AgentAction.objects.create(
            org=org,
            query_log_id=query_log_id,
            action_type=action_type,
            risk_level=safety_info["risk_level"],
            payload=action_payload,
            impact_summary=safety_info["impact_summary"],
            status="pending",
        )

        print(f"SUCCESS: AgentAction {action.id} created.")
        return str(action.id)

    except Exception as e:
        print(f"CRITICAL ERROR: Failed to create Pending Action: {str(e)}")
        return None
