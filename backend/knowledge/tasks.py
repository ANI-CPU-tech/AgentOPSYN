from celery import shared_task
from celery.utils.log import get_task_logger
from sentence_transformers import SentenceTransformer

from .chunker import chunk_text, extract_text_from_event
from .models import Embedding

logger = get_task_logger(__name__)

# Load model once at module level — reused across all Celery tasks in this worker
_model = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading Sentence Transformers model (first time)...")
        _model = SentenceTransformer("all-mpnet-base-v2")  # 768-dim vectors
    return _model


@shared_task(bind=True, max_retries=3)
def chunk_and_embed(
    self, event_id: str = None, runbook_id: str = None, source_type: str = "event"
):
    from accounts.models import Organization

    try:
        if source_type == "event":
            from integrations.models import Event

            source_obj = Event.objects.get(id=event_id)
            org = source_obj.org
            raw_text = extract_text_from_event(source_obj.normalized_payload)
            fk_kwargs = {"event": source_obj}

        # elif source_type=='runbook':
        #   from runbooks.models import Runbook
        #   source_obj=Runbook.objects.get(id=event_id)
        #   org=source_obj.org
        #   raw_text=f"{source_obj.title}\n\n{source_obj.content}"
        #   fk_kwargs={'runbook':source_obj}

        else:
            logger.error(f"Unknown source type: {source_type}")
            return

    except Exception as exc:
        logger.error(f"Could not fetch source object: {exc}")
        raise self.retry(exc=exc, countdown=5)

    if not raw_text.strip():
        logger.warning(
            f"Empty text for {source_type} {event_id or runbook_id} -- skipping..."
        )
        return

    chunks = chunk_text(raw_text)

    if not chunks:
        logger.warning("No chunks produced - skipping")
        return
    logger.info(
        f"Chunked into {len(chunks)} peices for {source_type} {event_id or runbook_id}"
    )
    try:
        model = get_model()
        vectors = model.encode(chunks, batch_size=32, show_progress_bar=False)
    except Exception as exc:
        logger.error(f"Embedding failed: {exc}")
        raise self.retry(exc=exc, countdown=10)

    existing_checkpoints = set(
        Embedding.objects.filter(
            org=org, chunk_index__in=range(len(chunks)), checkpoint=True, **fk_kwargs
        ).values_list("chunk_index", flat=True)
    )

    to_create = []
    for i, (chunk_text_piece, vector) in enumerate(zip(chunks, vectors)):
        if i in existing_checkpoints:
            logger.debug(f"Chunk {i} already checkpointed --skipping")
            continue

        to_create.append(
            Embedding(
                org=org,
                context_chunk=chunk_text_piece,
                embedding=vector.tolist(),
                chunk_index=i,
                checkpoint=True,
                **fk_kwargs,
            )
        )

    if to_create:
        Embedding.objects.bulk_create(to_create, batch_size=100)
        logger.info(f"Saved {len(to_create)} new embedding chunks.")

    if source_type == "event":
        source_obj.embedding_status = "done"
        source_obj.save(update_fields=["embedding_status"])

    logger.info(f"chunk_and_embed complete for {source_type} {event_id or runbook_id}")
