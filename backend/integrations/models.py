from django.db import models
import uuid
from accounts.models import Organization


class Integration(models.Model):
    SOURCE_CHOICES = [
        ("github", "GitHub"),
        ("jira", "Jira"),
        ("slack", "Slack"),
        ("notion", "Notion"),
        ("datadog", "Datadog"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="integrations"
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    config = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("org", "source")

    def __str__(self):
        return f"{self.org.name}->{self.source}"


class Event(models.Model):
    SOURCE_CHOICES = Integration.SOURCE_CHOICES
    EMBEDDING_STATUS = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("done", "Done"),
        ("failed", "Failed"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    idempotency_key = models.CharField(max_length=255, unique=True, db_index=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, db_index=True)
    event_type = models.CharField(max_length=100)
    raw_payload = models.JSONField()
    normalized_payload = models.JSONField(default=dict)
    org = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="events"
    )
    embedding_status = models.CharField(
        max_length=20, choices=EMBEDDING_STATUS, default="pending"
    )
    ingested_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"[{self.source}]{self.event_type}@{self.ingested_at:%Y-%m-%d %H:%M}"
