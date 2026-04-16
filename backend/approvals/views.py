from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdmin, IsAdminOrEngineer
from .models import AgentAction, AuditLog
from .serializers import AgentActionSerializer, AuditLogSerializer
from .safety import classify_risk
from .executor import execute_action


def _write_audit_log(action, actor, event, detail=""):
    """Helper — writes an immutable AuditLog entry."""
    AuditLog.objects.create(
        action=action,
        org=action.org,
        actor=actor,
        event=event,
        detail=detail,
        snapshot={
            "action_type": action.action_type,
            "risk_level": action.risk_level,
            "status": action.status,
            "payload": action.payload,
            "retry_count": action.retry_count,
        },
    )


class PendingActionsView(APIView):
    permission_classes = [IsAdminOrEngineer]

    def get(self, request):
        actions = AgentAction.objects.filter(
            org=request.user.org, status="pending"
        ).order_by("-created_at")
        return Response(AgentActionSerializer(actions, many=True).data)


class ActionDetailView(APIView):
    permission_classes = [IsAdminOrEngineer]

    def _get_action(self, pk, org):
        try:
            return AgentAction.objects.get(pk=pk, org=org)
        except AgentAction.DoesNotExist:
            return None

    def get(self, request, pk):
        action = self._get_action(pk, request.user.org)
        if not action:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(AgentActionSerializer(action).data)

    def put(self, request, pk):
        """Edit action payload before approving."""
        action = self._get_action(pk, request.user.org)
        if not action:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if action.status != "pending":
            return Response(
                {"detail": "Only pending actions can be edited."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Only allow editing payload — not risk level or type
        new_payload = request.data.get("payload")
        if new_payload:
            action.payload = new_payload
            # Re-classify risk with new payload
            risk_info = classify_risk(action.action_type, new_payload)
            action.risk_level = risk_info["risk_level"]
            action.impact_summary = risk_info["impact_summary"]
            action.save(update_fields=["payload", "risk_level", "impact_summary"])

            _write_audit_log(
                action, request.user, "edited", "Payload modified before approval"
            )

        return Response(AgentActionSerializer(action).data)


class ApproveActionView(APIView):
    permission_classes = [IsAdminOrEngineer]

    def post(self, request, pk):
        try:
            action = AgentAction.objects.get(pk=pk, org=request.user.org)
        except AgentAction.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if action.status != "pending":
            return Response(
                {"detail": f"Action is already {action.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark approved
        action.status = "approved"
        action.approved_by = request.user
        action.approved_at = timezone.now()
        action.save(update_fields=["status", "approved_by", "approved_at"])
        _write_audit_log(action, request.user, "approved")

        # Execute immediately after approval
        result = execute_action(action)

        if result["success"]:
            action.status = "executed"
            action.executed_at = timezone.now()
            action.execution_result = result["result"]
            action.save(update_fields=["status", "executed_at", "execution_result"])
            _write_audit_log(action, request.user, "executed", str(result["result"]))
        else:
            action.status = "failed"
            action.execution_result = {"error": result["error"]}
            action.save(update_fields=["status", "execution_result"])
            _write_audit_log(action, request.user, "failed", result["error"])

        return Response(
            {
                "status": action.status,
                "result": result["result"] if result["success"] else None,
                "error": result.get("error"),
            }
        )


class RejectActionView(APIView):
    permission_classes = [IsAdminOrEngineer]

    def post(self, request, pk):
        try:
            action = AgentAction.objects.get(pk=pk, org=request.user.org)
        except AgentAction.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if action.status != "pending":
            return Response(
                {"detail": f"Action is already {action.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get("reason", "No reason provided.")
        action.status = "rejected"
        action.rejection_reason = reason
        action.save(update_fields=["status", "rejection_reason"])
        _write_audit_log(action, request.user, "rejected", reason)

        return Response({"status": "rejected", "reason": reason})


class ActionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            action = AgentAction.objects.get(pk=pk, org=request.user.org)
        except AgentAction.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "status": action.status,
                "retry_count": action.retry_count,
                "execution_result": action.execution_result,
                "approved_at": action.approved_at,
                "executed_at": action.executed_at,
            }
        )


class AuditLogView(APIView):
    """Immutable full audit trail — Admin only."""

    permission_classes = [IsAdmin]

    def get(self, request):
        logs = (
            AuditLog.objects.filter(org=request.user.org)
            .select_related("action", "actor")
            .order_by("-created_at")[:200]
        )
        return Response(AuditLogSerializer(logs, many=True).data)
