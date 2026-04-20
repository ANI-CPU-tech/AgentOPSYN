import uuid
from django.db import models
from accounts.models import Organization, User


class AgentAction(models.Model):
    RISK_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("executed", "Executed"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    query_log = models.ForeignKey(
        "agent.QueryLog",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actions",
    )

    org = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="actions"
    )

    action_type = models.CharField(max_length=100)  # e.g. 'restart_service'
    risk_level = models.CharField(max_length=20, choices=RISK_CHOICES, default="medium")
    payload = models.JSONField(default=dict)  # action parameters
    impact_summary = models.TextField(blank=True)  # plain-English shown to human

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True
    )

    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_actions",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    execution_result = models.JSONField(default=dict)  # output of the action
    rejection_reason = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.risk_level.upper()}] {self.action_type} — {self.status}"


class AuditLog(models.Model):
    """
    Immutable record of every decision made on every AgentAction.
    Never deleted. Never updated. Append-only.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.ForeignKey(
        AgentAction, on_delete=models.CASCADE, related_name="audit_logs"
    )
    org = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="audit_logs"
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    event = models.CharField(
        max_length=50
    )  # 'approved', 'rejected', 'executed', 'failed'
    detail = models.TextField(blank=True)
    snapshot = models.JSONField(default=dict)  # full action state at this moment
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.event}] action:{self.action_id} by {self.actor}"
