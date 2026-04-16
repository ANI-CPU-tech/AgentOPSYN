import math
import numpy as np
from typing import List, Tuple
from sentence_transformers import SentenceTransformer
from django.db import connection
from .models import Embedding
from .tasks import get_model

CONFIDENCE_THRESHOLD = 0.45
ENTROPY_THRESHOLD = 4.0  # bits — above this = knowledge gap
MMR_LAMBDA = 0.7


def encode_query(query: str) -> list:
    model = get_model()
    return model.encode([query])[0].tolist()


def cosine_similarity(a: list, b: list) -> float:
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0


def mmr_rerank(query_vector: list, candidates: list, top_k: int = 5) -> list:
    """
    Maximal Marginal Relevance — balances relevance vs diversity.
    MMR = λ * Sim(query, doc) - (1-λ) * max Sim(doc, selected)
    λ = 0.7 (prioritise relevance, reduce duplicate runbooks)
    """
    if not candidates:
        return []

    selected = []
    remaining = list(candidates)
    while remaining and len(selected) < top_k:
        scores = []
        for candidate in remaining:
            relevance = cosine_similarity(query_vector, candidate["vector"])

            if selected:
                redundancy = max(
                    cosine_similarity(candidate["vector"], s["vector"])
                    for s in selected
                )
            else:
                redundancy = 0.0

            mmr_score = MMR_LAMBDA * relevance - (1 - MMR_LAMBDA) * redundancy
            scores.append((mmr_score, candidate))
        best = max(scores, key=lambda x: x[0])
        selected.append(best[1])
        remaining.remove(best[1])
    return selected


def shannon_entropy(vectors: list) -> float:
    """
    H(X) = -Σ P(xi) log2 P(xi)
    Computed over cosine similarities of top-k results.
    High entropy (> 2.1 bits) = results are too spread out = knowledge gap.
    """
    if not vectors or len(vectors) < 2:
        return 0.0
    sims = []
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            sims.append(cosine_similarity(vectors[i], vectors[j]))
    if not sims:
        return 0.0

    total = sum(sims) or 1.0
    probs = [s / total for s in sims]
    entropy = -sum(p * math.log2(p) for p in probs if p > 0)
    return entropy


def semantic_search(query: str, org_id: str, top_k: int = 10) -> dict:
    """
    Full RAG retrieval pipeline:
    1. Encode query → vector
    2. pgvector cosine similarity search (HNSW)
    3. MMR reranking for diversity
    4. Confidence scoring (Bayesian proxy via cosine sim)
    5. Shannon entropy for knowledge gap detection
    """
    query_vector = encode_query(query)

    # --- pgvector cosine similarity search ---
    with connection.cursor() as cursor:
        cursor.execute(  # change NULL as runbook_id to e.runbook_id once runbook app is done
            """
            SELECT
                e.id,
                e.context_chunk,
                e.chunk_index,
                e.event_id,
                NULL as runbook_id, 
                1 - (e.embedding <=> %s::vector) AS similarity
            FROM knowledge_embedding e
            WHERE e.org_id = %s
            ORDER BY e.embedding <=> %s::vector
            LIMIT %s
        """,
            [query_vector, org_id, query_vector, top_k * 2],
        )  # fetch 2x for MMR

        rows = cursor.fetchall()

    if not rows:
        return {
            "results": [],
            "confidence": 0.0,
            "gap_detected": True,
            "gap_reason": "No embeddings found for this org yet.",
        }

    # Build candidate dicts
    candidates = []
    for row in rows:
        emb = Embedding.objects.get(id=row[0])
        candidates.append(
            {
                "id": str(row[0]),
                "content": row[1],
                "chunk_index": row[2],
                "event_id": str(row[3]) if row[3] else None,
                "runbook_id": str(row[4]) if row[4] else None,
                "similarity": float(row[5]),
                "vector": emb.embedding,
            }
        )

    # --- MMR reranking ---
    reranked = mmr_rerank(query_vector, candidates, top_k=top_k)

    # --- Confidence score — average similarity of top results ---
    avg_similarity = sum(r["similarity"] for r in reranked) / len(reranked)
    confidence = round(avg_similarity, 4)

    # --- Knowledge gap detection via Shannon entropy ---
    vectors = [r["vector"] for r in reranked]
    entropy = shannon_entropy(vectors)
    gap_detected = entropy > ENTROPY_THRESHOLD or confidence < CONFIDENCE_THRESHOLD

    # Strip vectors from response (not needed by client)
    for r in reranked:
        del r["vector"]

    return {
        "results": reranked,
        "confidence": confidence,
        "gap_detected": gap_detected,
        "entropy": round(entropy, 4),
        "threshold": CONFIDENCE_THRESHOLD,
    }
