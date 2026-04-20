import requests
from .base import BaseAdapter


class NotionAdapter(BaseAdapter):
    def __init__(self, token=None):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

    def fetch_pages(self):
        """
        Crawls the Notion workspace for all accessible pages.
        Returns a list of dicts containing page ID, title, and raw text.
        """
        search_url = "https://api.notion.com/v1/search"
        # We filter for 'page' objects to avoid getting database schemas
        query = {"filter": {"value": "page", "property": "object"}}

        try:
            response = requests.post(
                search_url, json=query, headers=self.headers, timeout=15
            )
            response.raise_for_status()
            results = response.json().get("results", [])

            pages = []
            for page in results:
                page_id = page.get("id")
                # Extract the title from the nested properties
                properties = page.get("properties", {})
                title_data = properties.get("title", {}).get("title", [])
                title = (
                    title_data[0].get("plain_text", "Untitled")
                    if title_data
                    else "Untitled"
                )

                # Fetch the actual text content of the page
                content = self._get_page_content(page_id)

                pages.append(
                    {
                        "id": page_id,
                        "title": title,
                        "content": content,
                        "url": page.get("url", ""),
                    }
                )
            return pages
        except Exception as e:
            print(f"Notion API Error: {e}")
            return []

    def _get_page_content(self, page_id):
        """
        Notion pages are made of 'blocks'. This fetches the text from all
        paragraph blocks to create a searchable string for RAG.
        """
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        try:
            response = requests.get(blocks_url, headers=self.headers, timeout=10)
            blocks = response.json().get("results", [])

            text_chunks = []
            for block in blocks:
                block_type = block.get("type")
                # We mainly want paragraphs, headings, and lists
                if block_type in [
                    "paragraph",
                    "heading_1",
                    "heading_2",
                    "heading_3",
                    "bulleted_list_item",
                ]:
                    rich_text = block.get(block_type, {}).get("rich_text", [])
                    for text in rich_text:
                        text_chunks.append(text.get("plain_text", ""))

            return "\n".join(text_chunks)
        except:
            return ""

    def normalize(self, payload: dict, headers: dict) -> dict:
        """Handles incoming webhooks (existing logic)"""
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
        event_type = payload.get("type", "unknown")
        page_id = payload.get("page", {}).get("id", "unknown")
        ts = payload.get("page", {}).get("last_edited_time", "")
        return f"notion:{event_type}:{page_id}:{ts}"
