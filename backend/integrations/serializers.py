from rest_framework import serializers
from .models import Integration, Event


class IntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integration
        fields = ["id", "source", "is_active", "last_synced_at", "created_at"]
        read_only_fields = ["id", "created_at", "last_synced_at"]


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "source",
            "event_type",
            "normalized_payload",
            "embedding_status",
            "ingested_at",
        ]
        read_only_fields = fields
