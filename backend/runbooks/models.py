import uuid
from django.db import models
from accounts.models import Organization


class Runbook(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="runbooks"
    )
    query_log = models.ForeignKey(
        "agent.QueryLog",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="runbooks",
    )
    title = models.CharField(max_length=500)
    content = models.TextField()  # full markdown runbook
    version = models.IntegerField(default=1)

    # Self-referential FK for versioning history
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="versions",
    )

    # Hash of content used for cosine similarity duplicate detection
    similarity_hash = models.CharField(max_length=64, db_index=True, blank=True)
    is_archived = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[v{self.version}] {self.title}"
