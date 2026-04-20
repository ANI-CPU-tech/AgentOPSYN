import numpy as np
from knowledge.tasks import get_model


DUPLICATE_THRESHOLD = 0.95  # cosine similarity above this = duplicate


def find_duplicate(new_content: str, org_id: str):
    """
    Checks if a near-identical runbook already exists.
    Uses cosine similarity on the full runbook embedding.
    Returns the existing Runbook if duplicate found, else None.
    """
    from .models import Runbook
    from knowledge.models import Embedding

    model = get_model()
    new_vector = model.encode([new_content])[0]

    # Get all runbook embeddings for this org
    existing_embeddings = Embedding.objects.filter(
        org_id=org_id,
        runbook__isnull=False,
        chunk_index=0,  # use only first chunk for speed
    ).select_related("runbook")

    for emb in existing_embeddings:
        existing_vector = np.array(emb.embedding)
        new_vec = np.array(new_vector)

        # Cosine similarity
        denom = np.linalg.norm(existing_vector) * np.linalg.norm(new_vec)
        if denom == 0:
            continue
        similarity = float(np.dot(existing_vector, new_vec) / denom)

        if similarity >= DUPLICATE_THRESHOLD:
            return emb.runbook

    return None
