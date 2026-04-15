from rest_framework import serializers
from .models import Embedding


class EmbeddingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Embedding
        fields = [
            "id",
            "content_chunk",
            "chunk_index",
            "event_id",
            "runbook_id",
            "created_at",
        ]
        read_only_fields = fields
