from .base import BaseAdapter


class GitHubAdapter(BaseAdapter):
    def normalize(self, payload: dict, headers: dict) -> dict:
        event_type = headers.get("X-GitHub-Event", "unknown")
        actor = payload.get("sender", {}).get("login", "unknown")

        if event_type == "push":
            commits = payload.get("commits", [])
            title = f"Push to {payload.get('ref', '')} by {actor}"
            body = "\n".join(f"- {c['id'][:7]}: {c['message']}" for c in commits[:10])
            url = payload.get("compare", "")
        elif event_type == "pull_request":
            pr = payload.get("pull_request", {})
            title = f"PR #{pr.get('number')}: {pr.get('title')}"
            body = pr.get("body", "")
            url = pr.get("html_url", "")
        else:
            title = f"GitHub {event_type}"
            body = str(payload)[:500]
            url = ""

        return {
            "source": "github",
            "event_type": event_type,
            "title": title,
            "body": body,
            "actor": actor,
            "url": url,
            "timestamp": payload.get("repository", {}).get("pushed_at"),
            "metadata": {
                "repo": payload.get("repository", {}).get("full_name"),
                "ref": payload.get("ref"),
            },
        }

    def get_idempotency_key(self, payload: dict, headers: dict) -> str:
        delivery_id = headers.get("X-GitHub-Delivery", "")
        return f"github:{delivery_id}"
