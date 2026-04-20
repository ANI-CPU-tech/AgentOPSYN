from django.db import models
import uuid
from pgvector.django import VectorField
from accounts.models import Organization


class Embedding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        "integrations.Event",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="embeddings",
    )
    runbook = models.ForeignKey(
        "runbooks.Runbook",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="embeddings",
    )
    org = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="embeddings"
    )
    context_chunk = models.TextField()
    embedding = VectorField(dimensions=768)
    chunk_index = models.IntegerField()
    repo_name = models.CharField(max_length=255, blank=True, default="", db_index=True)
    checkpoint = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = []

    def __str__(self):
        source = (
            f"event:{self.event_id}" if self.event_id else f"runbook:{self.runbook_id}"
        )
        return f"Embedding Chunk {self.chunk_index}[{source}]"
