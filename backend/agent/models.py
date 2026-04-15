from django.db import models
import uuid
from accounts.models import Organization, User


class QueryLog(models.Model):
    SOURCE_CHOICES = [
        ("vscode", "VS Code"),
        ("dashboard", "Dashboard"),
        ("slack", "Slack"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="queries")
    org = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="queries"
    )
    query_text = models.TextField()
    response_text = models.TextField(blank=True, default="")
    confidence_score = models.FloatField(default=list)
    sources = models.JSONField(default=list)
    gap_detected = models.BooleanField(default=False)
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default="dashboard"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.source}] {self.query_text[:60]} - {self.user.email}"
