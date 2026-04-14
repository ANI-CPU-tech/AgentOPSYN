from .base import BaseAdapter


class NotionAdapter(BaseAdapter):
    def normalize(self, payload: dict, headers: dict) -> dict:
        page = payload.get("page", {})
        properties = page.get("properties", {})

        title_prop = properties.get("title", {})
        title_parts = title_prop.get("title", [{}])
        title = (
            title_parts[0].get("plain_text", "Untitled") if title_parts else "Untitled"
        )

        return {
            "source": "notion",
            "event_type": payload.get("type", "page.updated"),
            "title": title,
            "body": str(properties)[:1000],
            "actor": payload.get("authors", [{}])[0].get("name", "unknown")
            if payload.get("authors")
            else "unknown",
            "url": page.get("url", ""),
            "timestamp": page.get("last_edited_time"),
            "metadata": {
                "page_id": page.get("id"),
                "parent_type": page.get("parent", {}).get("type"),
            },
        }

    def get_idempotency_key(self, payload: dict, headers: dict) -> str:
        page_id = payload.get("page", {}).get("id", "unknown")
        ts = payload.get("page", {}).get("last_edited_time", "")
        return f"notion:{page_id}:{ts}"
