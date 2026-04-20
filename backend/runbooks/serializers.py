from rest_framework import serializers
from .models import Runbook


class RunbookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Runbook
        fields = [
            "id",
            "title",
            "content",
            "version",
            "similarity_hash",
            "is_archived",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "version",
            "similarity_hash",
            "incident_title",
            "incident_severity",
            "created_at",
            "updated_at",
        ]
