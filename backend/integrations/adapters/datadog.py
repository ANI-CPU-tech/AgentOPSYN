from .base import BaseAdapter


class DatadogAdapter(BaseAdapter):
    def normalize(self, payload: dict, headers: dict) -> dict:
        alert_id = payload.get("id", "unknown")
        title = payload.get("title", "Datadog Alert")
        body = payload.get("body", payload.get("text", ""))
        status = payload.get("alert_transition", payload.get("type", "unknown"))

        return {
            "source": "datadog",
            "event_type": "alert",
            "title": title,
            "body": body,
            "actor": "datadog",
            "url": payload.get("url", ""),
            "timestamp": payload.get("last_updated"),
            "metadata": {
                "alert_id": alert_id,
                "status": status,
                "priority": payload.get("priority"),
                "tags": payload.get("tags", []),
                "monitor_id": payload.get("monitor_id"),
            },
        }

    def get_idempotency_key(self, payload: dict, headers: dict) -> str:
        alert_id = payload.get("id", "unknown")
        status = payload.get("alert_transition", payload.get("type", "unknown"))
        ts = payload.get("last_updated", "")

        return f"datadog:{alert_id}:{status}:{ts}"
