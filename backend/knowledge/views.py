from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .retriever import semantic_search
from .tasks import chunk_and_embed
from .models import Embedding
from .serializers import EmbeddingSerializer


class SemanticSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        query = request.data.get("query", "").strip()
        top_k = int(request.data.get("top_k", 5))

        if not query:
            return Response(
                {"detail": "query is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        if top_k > 20:
            top_k = 20
        result = semantic_search(
            query=query, org_id=str(request.user.org_id), top_k=top_k
        )
        return Response(result, status=status.HTTP_200_OK)


class ManualIngestView(APIView):
    """
    Allows manually ingesting a plain text document into the knowledge base.
    Useful for importing existing docs, runbooks, or notes.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = request.data.get("text", "").strip()
        label = request.data.get("label", "manual_ingest")

        if not text:
            return Response(
                {"detail": "text is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Create a synthetic event to hold this manual doc
        from integrations.models import Event

        event = Event.objects.create(
            idempotency_key=f"manual:{label}:{hash(text)}",
            source="notion",  # treat manual ingests as notion-like docs
            event_type="manual_ingest",
            raw_payload={"text": text, "label": label},
            normalized_payload={
                "source": "notion",
                "event_type": "manual_ingest",
                "title": label,
                "body": text,
                "actor": str(request.user.id),
                "url": "",
                "timestamp": None,
                "metadata": {},
            },
            org=request.user.org,
        )

        chunk_and_embed.delay(event_id=str(event.id), source_type="event")

        return Response(
            {"detail": "Ingestion started.", "event_id": str(event.id)},
            status=status.HTTP_202_ACCEPTED,
        )
