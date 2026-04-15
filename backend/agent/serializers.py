from rest_framework import serializers
from .models import QueryLog


class QueryLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = QueryLog
        fields = [
            "id",
            "user_email",
            "query_text",
            "response_text",
            "confidence_score",
            "sources",
            "gap_detected",
            "source",
            "created_at",
        ]
        read_only_fields = fields
