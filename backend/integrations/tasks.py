import time
import random
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
import requests
from .crypto import decrypt_credential
from .adapters.notion import NotionAdapter
from knowledge.tasks import chunk_and_embed
from .models import Integration, Event
from django.utils import timezone

logger = get_task_logger(__name__)

MAX_RETRIES = 3
BASE_DELAY = 1
CAP_DELAY = 32
JITTER = 0.5


def exponential_backoff(retry_number: int) -> float:
    delay = min(CAP_DELAY, BASE_DELAY * (2**retry_number))
    jitter = random.uniform(0, JITTER)
    return delay + jitter


@shared_task(bind=True, max_retries=MAX_RETRIES)
def normalize_and_embed(self, event_id: str):
    """
    Fetches the Event, updates status to processing,
    then hands off to the knowledge app for chunking + embedding.
    Retries with exponential backoff on failure.
    """
    from .models import Event

    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        logger.error(f"Event {event_id} not found — skipping.")
        return

    event.embedding_status = "processing"
    event.save(update_fields=["embedding_status"])

    try:
        # Hand off to the knowledge app Celery task
        from knowledge.tasks import chunk_and_embed

        chunk_and_embed.delay(event_id=event_id, source_type="event")
        logger.info(f"Dispatched chunk_and_embed for event {event_id}")

    except Exception as exc:
        retry_num = self.request.retries
        delay = exponential_backoff(retry_num)
        logger.warning(
            f"normalize_and_embed failed for {event_id} "
            f"(attempt {retry_num + 1}/{MAX_RETRIES}). "
            f"Retrying in {delay:.1f}s. Error: {exc}"
        )

        event.embedding_status = "failed"
        event.save(update_fields=["embedding_status"])

        raise self.retry(exc=exc, countdown=delay)


@shared_task(bind=True)
def scrape_github_history(
    self, repo_full_name: str, org_id: str, user_id: str, limit: int = 50
):
    """
    Actively fetches recent commits from the GitHub REST API
    and ingests them into the knowledge base using the decrypted org token.
    """
    from integrations.models import Event, Integration
    from accounts.models import Organization
    from .crypto import decrypt_credential

    # ✨ 1. FETCH AND DECRYPT THE TOKEN ✨
    try:
        integration = Integration.objects.get(org_id=org_id, source="github")
        encrypted_token = integration.config.get("token")

        if not encrypted_token:
            logger.error(f"No GitHub token found in config for org {org_id}.")
            return

        real_token = decrypt_credential(encrypted_token)

        if not real_token:
            logger.error(f"Failed to decrypt GitHub token for org {org_id}.")
            return

    except Integration.DoesNotExist:
        logger.error(f"No GitHub integration found for org {org_id}.")
        return

    # ✨ 2. USE THE DECRYPTED TOKEN ✨
    headers = {
        "Authorization": f"Bearer {real_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    url = f"https://api.github.com/repos/{repo_full_name}/commits?per_page={limit}"

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        logger.error(f"GitHub API failed: {response.text}")
        return

    commits = response.json()
    logger.info(f"Fetched {len(commits)} commits from {repo_full_name}")

    org = Organization.objects.get(id=org_id)
    new_events_count = 0  # 🚀 Track how many are actually new

    # Process each commit into our standard Event format
    for commit in commits:
        sha = commit.get("sha")
        author = commit.get("commit", {}).get("author", {}).get("name", "unknown")
        message = commit.get("commit", {}).get("message", "")
        commit_url = commit.get("html_url", "")
        timestamp = commit.get("commit", {}).get("author", {}).get("date")

        # Check if we already ingested this commit
        idempotency_key = f"github_api_commit:{sha}"
        if Event.objects.filter(idempotency_key=idempotency_key).exists():
            continue

        normalized = {
            "source": "github",
            "event_type": "historical_commit",
            "title": f"Historical Commit by {author}",
            "body": message,
            "actor": author,
            "url": commit_url,
            "timestamp": timestamp,
            "metadata": {"repo": repo_full_name, "sha": sha},
        }

        # Save to database
        event = Event.objects.create(
            idempotency_key=idempotency_key,
            source="github",
            event_type="historical_commit",
            raw_payload=commit,
            normalized_payload=normalized,
            org=org,
        )

        # Send it to the RAG pipeline!
        from knowledge.tasks import chunk_and_embed

        chunk_and_embed.delay(event_id=str(event.id), source_type="event")
        new_events_count += 1

    # ✨ 3. UPDATE THE CLOCK SO THE FRONTEND KNOWS WE SYNCED ✨
    integration.last_synced_at = timezone.now()
    integration.save(update_fields=["last_synced_at"])

    logger.info(
        f"Successfully triggered embedding for {new_events_count} NEW commits in {repo_full_name}."
    )


@shared_task
def sync_all_github_repos():
    """Finds all active GitHub integrations and triggers a scrape for each."""
    from .models import Integration

    github_integrations = Integration.objects.filter(source="github", is_active=True)

    for integration in github_integrations:
        # ✨ SUPPORT THE NEW FRONTEND ARRAY FORMAT ✨
        repos = integration.config.get("repositories", [])

        # Fallback just in case you still have old data in the DB
        if not repos and integration.config.get("repo_full_name"):
            repos = [integration.config.get("repo_full_name")]

        for repo_name in repos:
            scrape_github_history.delay(
                repo_full_name=repo_name,
                org_id=str(integration.org.id),
                user_id="system-scheduler",
                limit=10,  # Smaller limit for periodic syncs
            )


@shared_task(bind=True)
def sync_notion_pages(self, integration_id: str, org_id: str):
    from integrations.models import Integration, Event
    from accounts.models import Organization
    from .crypto import decrypt_credential
    from knowledge.tasks import chunk_and_embed
    import requests
    from django.utils import timezone
    from celery.utils.log import get_task_logger

    logger = get_task_logger(__name__)

    try:
        integration = Integration.objects.get(id=integration_id)
        org = Organization.objects.get(id=org_id)
        db_token = integration.config.get("token", "")

        # 🚀 THE SMART BYPASS: Check if it's already plain text!
        if db_token.startswith("ntn_") or db_token.startswith("secret_"):
            logger.info("Token is plain text. Bypassing decryption.")
            real_token = db_token
        else:
            logger.info("Token appears encrypted. Attempting decryption...")
            real_token = decrypt_credential(db_token)

        if not real_token:
            logger.error(f"Failed to resolve a valid Notion token for org {org_id}.")
            return "Token Resolution Failed"

        # 🚀 2. SET CORRECT HEADERS
        headers = {
            "Authorization": f"Bearer {real_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",  # Current stable version
        }

        # ✨ 3. FETCH PAGES
        search_url = "https://api.notion.com/v1/search"
        payload = {"filter": {"value": "page", "property": "object"}}

        response = requests.post(search_url, json=payload, headers=headers)

        if response.status_code != 200:
            logger.error(f"Notion API Error: {response.status_code} {response.text}")
            return f"API Error: {response.status_code}"

        pages = response.json().get("results", [])
        new_pages_count = 0

        # ✨ 4. PROCESS AND INGEST EACH PAGE
        for page in pages:
            page_id = page.get("id")
            url = page.get("url", "")
            last_edited_time = page.get("last_edited_time")

            # Extract title safely (Notion nests properties deeply)
            title = "Untitled Page"
            try:
                properties = page.get("properties", {})
                for key, prop in properties.items():
                    if prop.get("type") == "title":
                        title_arr = prop.get("title", [])
                        if title_arr:
                            title = title_arr[0].get("plain_text", "Untitled")
                        break
            except Exception:
                pass

            # 🚀 NEW: Fetch the actual text inside the page!
            page_content = get_notion_page_text(page_id, headers)

            # Create an idempotency key using the last edited time
            # This ensures we only re-embed if the page has actually changed
            idempotency_key = f"notion_page:{page_id}:{last_edited_time}"
            if Event.objects.filter(idempotency_key=idempotency_key).exists():
                continue

            normalized = {
                "source": "notion",
                "event_type": "page_updated",
                "title": f"Notion Page: {title}",
                "body": page_content,  # 🚀 NEW: Feed the actual text to the RAG pipeline
                "actor": "Notion Integration",
                "url": url,
                "timestamp": last_edited_time,
                "metadata": {"page_id": page_id},
            }

            # Save to database
            event = Event.objects.create(
                idempotency_key=idempotency_key,
                source="notion",
                event_type="page_updated",
                raw_payload=page,
                normalized_payload=normalized,
                org=org,
            )

            # Send it to the RAG pipeline!
            chunk_and_embed.delay(event_id=str(event.id), source_type="event")
            new_pages_count += 1

        # 🚀 5. UPDATE TIMESTAMP
        integration.last_synced_at = timezone.now()
        integration.save(update_fields=["last_synced_at"])

        logger.info(
            f"Successfully triggered embedding for {new_pages_count} NEW Notion pages."
        )
        return f"Successfully synced {new_pages_count} new/updated pages out of {len(pages)} total."

    except Exception as e:
        logger.error(f"Notion Sync Crash: {str(e)}")
        return str(e)


def get_notion_page_text(page_id: str, headers: dict) -> str:
    """Fetches the blocks inside a Notion page and extracts the plain text."""
    import requests

    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return ""

    blocks = response.json().get("results", [])
    text_content = []

    for block in blocks:
        block_type = block.get("type")
        # Notion nests text deeply depending on if it's a paragraph, heading, etc.
        if block_type and isinstance(block.get(block_type), dict):
            rich_text_array = block[block_type].get("rich_text", [])
            for text_obj in rich_text_array:
                text_content.append(text_obj.get("plain_text", ""))

    return "\n".join(text_content)
