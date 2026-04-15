from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from knowledge.retriever import semantic_search
from .ollama_client import is_ollama_running
from .pipeline import run_agent_pipeline
from .models import QueryLog
from .serializers import QueryLogSerializer


class QueryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        query_text = request.data.get("query", "").strip()
        top_k = int(request.data.get("top_k", 10))
        query_source = request.data.get("source", "dashboard")

        if not query_text:
            return Response(
                {"detail": "query is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        # --- Step 1: Semantic retrieval from knowledge base ---
        retrieval = semantic_search(
            query=query_text,
            org_id=str(request.user.org_id),
            top_k=top_k,
        )

        # --- Step 2: Knowledge gap → return fallback immediately ---
        if retrieval["gap_detected"]:
            query_log = QueryLog.objects.create(
                user=request.user,
                org=request.user.org,
                query_text=query_text,
                response_text="Knowledge gap detected — insufficient context to answer.",
                confidence_score=retrieval["confidence"],
                sources=[],
                gap_detected=True,
                source=query_source,
            )
            return Response(
                {
                    "answer": (
                        "I don't have enough information in the knowledge base to answer this confidently. "
                        "Consider ingesting more relevant documents or runbooks."
                    ),
                    "confidence": retrieval["confidence"],
                    "gap_detected": True,
                    "sources": [],
                    "query_id": str(query_log.id),
                },
                status=status.HTTP_200_OK,
            )

        # --- Step 3: Check Ollama is running ---
        if not is_ollama_running():
            return Response(
                {"detail": "Ollama is not running. Start it with: ollama serve"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # --- Step 4: Save initial QueryLog (we'll update it after pipeline) ---
        query_log = QueryLog.objects.create(
            user=request.user,
            org=request.user.org,
            query_text=query_text,
            confidence_score=retrieval["confidence"],
            sources=retrieval["results"],
            gap_detected=False,
            source=query_source,
        )

        # --- Step 5: Run Planner → Executor → Validator pipeline ---
        try:
            pipeline_result = run_agent_pipeline(
                query=query_text,
                retrieval_results=retrieval["results"],
                org_id=str(request.user.org_id),
                query_log_id=str(query_log.id),
                user=request.user,
            )
        except RuntimeError as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # --- Step 6: Update QueryLog with final answer ---
        query_log.response_text = pipeline_result["answer"]
        query_log.save(update_fields=["response_text"])

        return Response(
            {
                "answer": pipeline_result["answer"],
                "confidence": retrieval["confidence"],
                "gap_detected": False,
                "sources": retrieval["results"],
                "steps": pipeline_result["steps"],
                "needs_approval": pipeline_result["needs_approval"],
                "pending_action_id": pipeline_result.get("pending_action_id"),
                "replan_count": pipeline_result["replan_count"],
                "query_id": str(query_log.id),
            },
            status=status.HTTP_200_OK,
        )


class QueryHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logs = QueryLog.objects.filter(org=request.user.org).order_by("-created_at")[
            :50
        ]
        return Response(QueryLogSerializer(logs, many=True).data)


class QueryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            log = QueryLog.objects.get(pk=pk, org=request.user.org)
        except QueryLog.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(QueryLogSerializer(log).data)
