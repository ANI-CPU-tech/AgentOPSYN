from agent.ollama_client import chat


def build_runbook_prompt_from_query(query_log) -> str:
    """Builds a runbook prompt from a resolved query session."""
    return f"""
Query: {query_log.query_text}

Answer Given:
{query_log.response_text}

Confidence Score: {query_log.confidence_score}
Source: {query_log.source}
Timestamp: {query_log.created_at}
"""


def generate_runbook_content(prompt: str) -> str:
    """Unchanged — still calls Llama 3."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are OPSYN. Given a resolved developer query and its answer, "
                "generate a clear runbook in markdown with these sections:\n"
                "## Summary\n"
                "## Problem Description\n"
                "## Investigation Steps\n"
                "## Resolution Steps\n"
                "## Prevention\n"
                "Be concise and actionable."
            ),
        },
        {"role": "user", "content": f"Generate a runbook for:\n\n{prompt}"},
    ]
    return chat(messages, temperature=0.1)
