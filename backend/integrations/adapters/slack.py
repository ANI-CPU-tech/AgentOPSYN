from .base import BaseAdapter


class SlackAdapter(BaseAdapter):
    def normalize(self, payload: dict, headers: dict) -> dict:
        event = payload.get("event", {})
        event_type = event.get("type", payload.get("type", "unknown"))
        actor = event.get("user", "unknown")
        text = event.get("text", "")
        channel = event.get("channel", "")

        return {
            "source": "slack",
            "event_type": event_type,
            "title": f"Slack message in #{channel}",
            "body": text,
            "actor": actor,
            "url": "",
            "timestamp": event.get("ts"),
            "metadata": {
                "channel": channel,
                "thread_ts": event.get("thread_ts"),
                "team_id": payload.get("team_id"),
            },
        }

    def get_idempotency_key(self, payload: dict, headers: dict) -> str:
        event_id = payload.get("event_id")
        if event_id:
            return f"slack:{event_id}"

        # fallback (rare)
        ts = payload.get("event", {}).get("ts", "")
        return f"slack:fallback:{ts}"
