import time
import random
from celery import shared_task
from celery.utils.log import get_task_logger

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
        # from knowledge.tasks import chunk_and_embed

        # chunk_and_embed.delay(event_id=event_id, source_type="event")
        print(f"[STUB] Would embed event {event_id} — knowledge app not built yet")
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
