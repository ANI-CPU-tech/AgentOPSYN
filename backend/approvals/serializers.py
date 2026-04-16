from rest_framework import serializers
from .models import AgentAction, AuditLog


class AgentActionSerializer(serializers.ModelSerializer):
    approved_by_email = serializers.EmailField(
        source="approved_by.email", read_only=True
    )

    class Meta:
        model = AgentAction
        fields = [
            "id",
            "action_type",
            "risk_level",
            "payload",
            "impact_summary",
            "status",
            "approved_by_email",
            "approved_at",
            "executed_at",
            "execution_result",
            "rejection_reason",
            "retry_count",
            "created_at",
        ]
        read_only_fields = fields


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source="actor.email", read_only=True)
    action_type = serializers.CharField(source="action.action_type", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action_type",
            "actor_email",
            "event",
            "detail",
            "snapshot",
            "created_at",
        ]
        read_only_fields = fields
