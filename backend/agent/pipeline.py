import json
from typing import Optional
from .ollama_client import chat

CONFIDENCE_THRESHOLD = 0.40
MAX_REPLAN_ATTEMPTS = 2


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


def classify_risk(action_type: str, action_payload: dict) -> str:
    """
    Context-aware risk classification.
    Returns: 'low' | 'medium' | 'high' | 'critical'
    """
    action_lower = action_type.lower()

    if any(word in action_lower for word in ("delete", "drop", "destroy", "terminate")):
        return "critical"
    if any(
        word in action_lower for word in ("restart", "redeploy", "rollback", "scale")
    ):
        return "high"
    if any(word in action_lower for word in ("update", "patch", "modify", "create")):
        return "medium"
    return "low"


# ─────────────────────────────────────────────
# PLANNER
# ─────────────────────────────────────────────


def run_planner(query: str, context: str) -> list:
    """
    Decomposes the user query into a list of executable steps.
    Returns a list of step strings.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are OPSYN, an expert DevOps AI assistant. "
                "Given a user query and relevant context from the knowledge base, "
                "decompose the goal into a short numbered list of concrete steps to resolve it. "
                "Be specific. Max 5 steps. Output ONLY the steps as a JSON array of strings. "
                'Example: ["Check recent GitHub commits", "Inspect Datadog alert", "Restart auth service"]'
            ),
        },
        {"role": "user", "content": f"Query: {query}\n\nContext:\n{context}"},
    ]

    response = chat(messages, temperature=0.1)

    # Parse JSON steps from response
    try:
        # Strip any markdown fences if Llama wraps it
        clean = response.strip().strip("`").replace("json\n", "").strip()
        steps = json.loads(clean)
        if isinstance(steps, list):
            return [str(s) for s in steps]
    except Exception:
        pass

    # Fallback — treat whole response as single step
    return [response]


# ─────────────────────────────────────────────
# EXECUTOR
# ─────────────────────────────────────────────


def run_executor(query: str, context: str, steps: list) -> dict:
    """
    Executes the planned steps using Llama 3 as the reasoning engine.
    Returns {answer, action_type, action_payload, needs_approval}
    """
    steps_str = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))

    messages = [
        {
            "role": "system",
            "content": (
                "You are OPSYN, an expert DevOps AI assistant. "
                "Given the user query, relevant context, and a plan of steps, "
                "provide a clear answer AND if an executable action is needed, specify it. "
                "Respond ONLY with a JSON object with these keys:\n"
                "- answer: string (your human-readable response with citations)\n"
                "- action_type: string or null (e.g. 'restart_service', 'create_jira_ticket', null if no action needed)\n"
                "- action_payload: object or null (details of the action)\n"
                "- needs_approval: boolean (true if action is risky and needs human sign-off)\n"
                "Always cite your sources using [Source N] notation."
            ),
        },
        {
            "role": "user",
            "content": (f"Query: {query}\n\nPlan:\n{steps_str}\n\nContext:\n{context}"),
        },
    ]

    response = chat(messages, temperature=0.2)

    try:
        clean = response.strip().strip("`").replace("json\n", "").strip()
        result = json.loads(clean)
        return {
            "answer": result.get("answer", response),
            "action_type": result.get("action_type"),
            "action_payload": result.get("action_payload", {}),
            "needs_approval": result.get("needs_approval", False),
        }
    except Exception:
        # Fallback — treat as plain answer, no action
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
    """
    Checks whether the executor's answer actually addresses the query.
    Returns {is_valid, reason, needs_replan}
    """
    steps_str = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))

    messages = [
        {
            "role": "system",
            "content": (
                "You are a validator for OPSYN. "
                "Check if the given answer adequately addresses the original query "
                "and covers the planned steps. "
                "Respond ONLY with a JSON object:\n"
                "- is_valid: boolean\n"
                "- reason: string (short explanation)\n"
                "- needs_replan: boolean (true if the answer is off-track or incomplete)"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Original Query: {query}\n\n"
                f"Planned Steps:\n{steps_str}\n\n"
                f"Answer Produced:\n{answer}"
            ),
        },
    ]

    response = chat(messages, temperature=0.0)

    try:
        clean = response.strip().strip("`").replace("json\n", "").strip()
        result = json.loads(clean)
        return {
            "is_valid": result.get("is_valid", True),
            "reason": result.get("reason", ""),
            "needs_replan": result.get("needs_replan", False),
        }
    except Exception:
        return {"is_valid": True, "reason": "", "needs_replan": False}


# ─────────────────────────────────────────────
# MAIN PIPELINE — Planner → Executor → Validator
# ─────────────────────────────────────────────


def run_agent_pipeline(
    query: str,
    retrieval_results: list,
    org_id: str,
    query_log_id: str,
    user,
) -> dict:
    """
    Full Planner → Executor → Validator loop.
    Auto-replans up to MAX_REPLAN_ATTEMPTS times if validator flags issues.
    Creates AgentAction rows for high-risk actions needing human approval.
    """
    context = build_context_string(retrieval_results)
    replan_count = 0
    steps = []
    execution_result = {}

    while replan_count <= MAX_REPLAN_ATTEMPTS:
        # 1. PLAN
        steps = run_planner(query, context)

        # 2. EXECUTE
        execution_result = run_executor(query, context, steps)

        # 3. VALIDATE
        validation = run_validator(query, execution_result["answer"], steps)

        if validation["is_valid"] and not validation["needs_replan"]:
            break  # ✅ good answer — exit loop

        replan_count += 1
        if replan_count > MAX_REPLAN_ATTEMPTS:
            # After max replans, go with what we have
            break

    # 4. Handle action requiring approval
    pending_action_id = None
    if execution_result.get("action_type") and execution_result.get("needs_approval"):
        pending_action_id = _create_pending_action(
            action_type=execution_result["action_type"],
            action_payload=execution_result["action_payload"],
            query_log_id=query_log_id,
            user=user,
            org_id=org_id,
        )

    return {
        "answer": execution_result.get("answer", ""),
        "steps": steps,
        "action_type": execution_result.get("action_type"),
        "needs_approval": execution_result.get("needs_approval", False),
        "pending_action_id": pending_action_id,
        "replan_count": replan_count,
    }


def _create_pending_action(
    action_type: str,
    action_payload: dict,
    query_log_id: str,
    user,
    org_id: str,
) -> Optional[str]:
    """Creates an AgentAction row in the approvals app for human review."""
    try:
        # Import here to avoid circular imports
        # from approvals.models import AgentAction
        # from accounts.models import Organization
        #
        # org = Organization.objects.get(id=org_id)
        # risk_level = classify_risk(action_type, action_payload)
        #
        # # Build a plain-English impact summary
        # impact_summary = (
        #     f"Action: {action_type}\n"
        #     f"Risk Level: {risk_level.upper()}\n"
        #     f"Payload: {json.dumps(action_payload, indent=2)}"
        # )
        #
        # action = AgentAction.objects.create(
        #     query_log_id=query_log_id,
        #     action_type=action_type,
        #     risk_level=risk_level,
        #     payload=action_payload,
        #     impact_summary=impact_summary,
        #     status="pending",
        #     org=org,
        # )
        # return str(action.id)
        pass

    except Exception as e:
        return None
