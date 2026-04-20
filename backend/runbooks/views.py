from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdmin
from knowledge.retriever import semantic_search
from .models import Runbook
from .serializers import RunbookSerializer


class RunbookListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        runbooks = Runbook.objects.filter(
            org=request.user.org, is_archived=False
        ).order_by("-created_at")[:50]
        return Response(RunbookSerializer(runbooks, many=True).data)

    def post(self, request):
        """Manually create a runbook."""
        title = request.data.get("title", "").strip()
        content = request.data.get("content", "").strip()

        if not title or not content:
            return Response(
                {"detail": "title and content are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        runbook = Runbook.objects.create(
            org=request.user.org,
            title=title,
            content=content,
        )

        # Embed it immediately
        from knowledge.tasks import chunk_and_embed

        chunk_and_embed.delay(runbook_id=str(runbook.id), source_type="runbook")

        return Response(RunbookSerializer(runbook).data, status=status.HTTP_201_CREATED)


class RunbookDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, pk, org):
        try:
            return Runbook.objects.get(pk=pk, org=org)
        except Runbook.DoesNotExist:
            return None

    def get(self, request, pk):
        runbook = self._get(pk, request.user.org)
        if not runbook:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(RunbookSerializer(runbook).data)

    def put(self, request, pk):
        """Manually update a runbook — creates a new version."""
        runbook = self._get(pk, request.user.org)
        if not runbook:
            return Response(status=status.HTTP_404_NOT_FOUND)

        new_content = request.data.get("content")
        if not new_content:
            return Response(
                {"detail": "content is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        runbook.content = new_content
        runbook.version += 1
        runbook.save(update_fields=["content", "version", "updated_at"])

        # Re-embed updated content
        from knowledge.tasks import chunk_and_embed

        chunk_and_embed.delay(runbook_id=str(runbook.id), source_type="runbook")

        return Response(RunbookSerializer(runbook).data)

    def delete(self, request, pk):
        runbook = self._get(pk, request.user.org)
        if not runbook:
            return Response(status=status.HTTP_404_NOT_FOUND)
        runbook.is_archived = True
        runbook.save(update_fields=["is_archived"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class RunbookVersionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            runbook = Runbook.objects.get(pk=pk, org=request.user.org)
        except Runbook.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        versions = Runbook.objects.filter(parent=runbook).order_by("-version")
        return Response(RunbookSerializer(versions, many=True).data)


class RunbookSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        query = request.data.get("query", "").strip()
        if not query:
            return Response(
                {"detail": "query is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        results = semantic_search(query=query, org_id=str(request.user.org_id), top_k=5)

        # Filter to only runbook results
        runbook_results = [r for r in results["results"] if r.get("runbook_id")]

        return Response(
            {
                "results": runbook_results,
                "confidence": results["confidence"],
                "gap_detected": results["gap_detected"],
            }
        )
