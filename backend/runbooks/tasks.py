import hashlib
from celery import shared_task
from celery.utils.log import get_task_logger
from .ollama_builder import build_runbook_prompt_from_query, generate_runbook_content
from .duplicate_detector import find_duplicate

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_runbook(self, query_log_id: str):
    """
    Auto-generates a runbook after incident resolution.
    Full timeline: alert → context → action → outcome
    Checks for duplicates via cosine similarity before saving.
    Re-embeds into pgvector within 20s of creation.
    """
    try:
        from agent.models import QueryLog
        from .models import Runbook

        query_log = QueryLog.objects.get(id=query_log_id)
        org = query_log.org
        existing_runbook = Runbook.objects.filter(query_log=query_log).first()
        prompt = build_runbook_prompt_from_query(query_log)
        # Generate runbook content via Llama 3
        content = generate_runbook_content(prompt)

        if not content:
            logger.error(f"Empty runbook generated for incident {incident_id}")
            return

        # Compute similarity hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:64]

        # Duplicate detection
        duplicate = find_duplicate(content, str(org.id))

        if duplicate and not existing_runbook:
            # Merge — update the existing duplicate instead of creating new
            logger.info(
                f"Near-duplicate detected — merging with runbook {duplicate.id}"
            )
            duplicate.content = content
            duplicate.version += 1
            duplicate.similarity_hash = content_hash
            duplicate.save(
                update_fields=["content", "version", "similarity_hash", "updated_at"]
            )
            runbook = duplicate
        elif existing_runbook:
            # New version of existing runbook
            existing_runbook.content = content
            existing_runbook.version += 1
            existing_runbook.similarity_hash = content_hash
            existing_runbook.save(
                update_fields=["content", "version", "similarity_hash", "updated_at"]
            )
            runbook = existing_runbook
        else:
            # Brand new runbook
            runbook = Runbook.objects.create(
                query_log=query_log,
                org=org,
                title=f"Runbook: {query_log.query_text[:100]}",
                content=content,
                similarity_hash=content_hash,
            )

        logger.info(f"Runbook {runbook.id} saved (v{runbook.version})")

        # Re-embed into pgvector — target: within 20 seconds
        from knowledge.tasks import chunk_and_embed

        chunk_and_embed.delay(runbook_id=str(runbook.id), source_type="runbook")

    except Exception as exc:
        logger.error(f"generate_runbook failed for incident {query_log_id}: {exc}")
        raise self.retry(exc=exc, countdown=15)
