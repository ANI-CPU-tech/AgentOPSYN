from accounts import permissions
import django_redis
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .adapters import get_adapter
from .authentication import APIKeyAuthentication
from .models import Integration, Event
from .serializers import IntegrationSerializer, EventSerializer
from .tasks import normalize_and_embed
from accounts.permissions import IsAdmin, IsAdminOrEngineer

from integrations import serializers


class WebhookReceiverView(APIView):
    """
    Single view handles all 5 webhook sources.
    Source is passed as a URL kwarg e.g. /api/webhooks/github/
    """

    authentication_classes = [APIKeyAuthentication]
    permission_classes = []

    def post(self, request, source):
        if source not in ("github", "jira", "slack", "notion", "datadog"):
            return Response(
                {"detail": "Unknown source."}, status=status.HTTP_404_NOT_FOUND
            )

        adapter = get_adapter(source)
        headers = dict(request.headers)
        payload = request.data
        idempotency_key = adapter.get_idempotency_key(payload, headers)
        cache_key = f"idempotency:{idempotency_key}"

        if cache.get(cache_key):
            return Response({"detail": "duplicate, skipped"}, status=status.HTTP_200_OK)

        cache.set(cache_key, "1", timeout=86400)

        try:
            normalized = adapter.normalized(payload, headers)
        except Exception as e:
            return Response(
                {"detail": f"Normalization failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event = Event.objects.create(
            idempotency_key=idempotency_key,
            source=source,
            event_type=normalized["event_type"],
            raw_payload=payload,
            normalized_payload=normalized,
            org=request.user.org,
        )

        normalize_and_embed.delay(str(event.id))
        return Response({"event_id": str(event.id)}, status=HTTP_202_ACCEPTED)


class IntegrationListCreateView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        integrations = Integration.objects.filter(org=request.user.org)
        return Response(IntegrationSerializer(integrations, many=True).data)

    def post(self, request):
        serializer = IntegrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(org=request.user.org)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class IntegrationDetailView(APIView):
    permission_classes = [IsAdmin]

    def _get_integration(self, pk, org):
        try:
            return Integration.objects.get(pk=pk, org=org)
        except Integration.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get_integration(pk, request.user.org)
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(IntegrationSerializer(obj).data)

    def put(self, request, pk):
        obj = self._get_integration(pk, request.user.org)
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = IntegrationSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        obj = self._get_integration(pk, request.user.org)
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class EventListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        events = Event.objects.filter(org=request.user.org).order_by("-ingested_at")[
            :100
        ]
        return Response(EventSerializer(events, many=True).data)


class EventDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            event = Event.objects.get(pk=pk, org=request.user.org)
        except Event.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(EventSerializer(event).data)
