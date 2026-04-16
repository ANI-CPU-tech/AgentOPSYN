from datetime import datetime


RISK_MATRIX = {
    # keyword → (base_risk, description)
    "delete": ("critical", "Permanently deletes a resource"),
    "drop": ("critical", "Drops a database or resource"),
    "destroy": ("critical", "Destroys infrastructure"),
    "terminate": ("critical", "Terminates a running process or instance"),
    "restart": ("high", "Restarts a live service — may cause brief downtime"),
    "redeploy": ("high", "Redeploys a service — may cause brief downtime"),
    "rollback": ("high", "Rolls back to a previous version"),
    "scale": ("high", "Scales a service up or down"),
    "update": ("medium", "Updates a configuration or resource"),
    "patch": ("medium", "Applies a patch to a running system"),
    "create": ("medium", "Creates a new resource"),
    "send_alert": ("low", "Sends a notification — no system impact"),
    "create_ticket": ("low", "Creates a Jira ticket — no system impact"),
    "notify": ("low", "Sends a message — no system impact"),
}


def classify_risk(
    action_type: str, payload: dict, environment: str = "production"
) -> dict:
    """
    Context-aware risk classification from your slides.
    Same action scored differently based on environment + time of day.

    Returns:
    {
        risk_level: 'low' | 'medium' | 'high' | 'critical',
        impact_summary: str,
        needs_approval: bool,
    }
    """
    action_lower = action_type.lower()

    # Match against risk matrix
    base_risk = "low"
    description = "Unknown action type"
    for keyword, (risk, desc) in RISK_MATRIX.items():
        if keyword in action_lower:
            base_risk = risk
            description = desc
            break

    # Elevate risk in production environment
    risk_levels = ["low", "medium", "high", "critical"]
    risk_index = risk_levels.index(base_risk)

    if environment == "production" and risk_index < 3:
        risk_index = min(risk_index + 1, 3)  # bump up one level in prod

    # Elevate risk outside business hours (extra caution)
    hour = datetime.now().hour
    is_off_hours = hour < 8 or hour > 20
    if is_off_hours and risk_index < 3:
        risk_index = min(risk_index + 1, 3)

    final_risk = risk_levels[risk_index]
    needs_approval = final_risk in ("medium", "high", "critical")

    impact_summary = (
        f"Action: {action_type}\n"
        f"Risk Level: {final_risk.upper()}\n"
        f"Environment: {environment}\n"
        f"Off-hours: {'Yes ⚠️' if is_off_hours else 'No'}\n"
        f"Description: {description}\n"
        f"Payload: {payload}"
    )

    return {
        "risk_level": final_risk,
        "impact_summary": impact_summary,
        "needs_approval": needs_approval,
    }
