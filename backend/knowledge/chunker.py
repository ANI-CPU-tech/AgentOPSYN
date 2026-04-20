from typing import List

CHUNK_SIZE = 512  # tokens
OVERLAP = 50  # tokens


def simple_token_count(text: str) -> int:
    """Rough token estimate — 1 token ≈ 4 characters."""
    return len(text) // 4


def chunk_text(
    text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP
) -> List[str]:
    """
    Splits text into overlapping chunks of approximately chunk_size tokens.
    Uses sentence-aware splitting to avoid cutting mid-sentence.
    """
    if not text or not text.strip():
        return []

    # Split into sentences first (preserve context)
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())

    chunks = []
    current_chunk = []
    current_size = 0

    for sentence in sentences:
        sentence_size = simple_token_count(sentence)

        if current_size + sentence_size > chunk_size and current_chunk:
            # Save current chunk
            chunks.append(" ".join(current_chunk))

            # Keep last `overlap` tokens worth of sentences for next chunk
            overlap_chunk = []
            overlap_size = 0
            for s in reversed(current_chunk):
                s_size = simple_token_count(s)
                if overlap_size + s_size <= overlap:
                    overlap_chunk.insert(0, s)
                    overlap_size += s_size
                else:
                    break

            current_chunk = overlap_chunk
            current_size = overlap_size

        current_chunk.append(sentence)
        current_size += sentence_size

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def extract_text_from_event(normalized_payload: dict) -> str:
    """Pull the most useful text fields out of a normalized event payload."""
    parts = []
    for field in ("title", "body", "url", "actor"):
        val = normalized_payload.get(field)
        if val:
            parts.append(str(val))

    metadata = normalized_payload.get("metadata", {})
    if metadata:
        parts.append(str(metadata))

    return "\n".join(parts)
