from .base import BaseAdapter


class JiraAdapter(BaseAdapter):
    def normalize(self, payload: dict, headers: dict) -> dict:
        event_type = payload.get("webhookEvent", "unknown")
        issue = payload.get("issue", {})
        fields = issue.get("fields", {})
        actor = payload.get("user", {}).get("displayName", "unknown")

        return {
            "source": "jira",
            "event_type": event_type,
            "title": f"[{issue.get('key')}] {fields.get('summary', '')}",
            "body": fields.get("description", "") or "",
            "actor": actor,
            "url": f"https://your-domain.atlassian.net/browse/{issue.get('key', '')}",
            "timestamp": payload.get("timestamp"),
            "metadata": {
                "issue_key": issue.get("key"),
                "status": fields.get("status", {}).get("name"),
                "priority": fields.get("priority", {}).get("name"),
                "issue_type": fields.get("issuetype", {}).get("name"),
            },
        }

    def get_idempotency_key(self, payload: dict, headers: dict) -> str:
        event = payload.get("webhookEvent", "unknown")
        issue_id = payload.get("issue", {}).get("id", "unknown")
        timestamp = payload.get("timestamp", "")

        return f"jira:{event}:{issue_id}:{timestamp}"
