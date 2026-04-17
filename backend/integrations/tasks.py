import time
import random
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
import requests
from .crypto import decrypt_credential

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

    # Process each commit into our standard Event format
    for commit in commits:
        sha = commit.get("sha")
        author = commit.get("commit", {}).get("author", {}).get("name", "unknown")
        message = commit.get("commit", {}).get("message", "")
        url = commit.get("html_url", "")
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
            "url": url,
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

    logger.info(f"Successfully triggered embedding for {repo_full_name} history.")


@shared_task
def sync_all_github_repos():
    """Finds all active GitHub integrations and triggers a scrape for each."""
    from .models import Integration

    github_integrations = Integration.objects.filter(source="github", is_active=True)

    for integration in github_integrations:
        repo_name = integration.config.get("repo_full_name")
        if repo_name:
            scrape_github_history.delay(
                repo_full_name=repo_name,
                org_id=str(integration.org.id),
                user_id="system-scheduler",
                limit=10,  # Smaller limit for periodic syncs
            )
