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
from .handshakes import verify_github, verify_jira, verify_slack
from .crypto import encrypt_credential


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
            normalized = adapter.normalize(payload, headers)
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
        return Response({"event_id": str(event.id)}, status=status.HTTP_202_ACCEPTED)


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

        # 1. Make a mutable copy of the request data
        data = request.data.copy()
        config = data.get("config", {})
        source = obj.source

        # ✨ 2. VERIFICATION & ENCRYPTION BLOCK (Only if new token is provided) ✨
        if source == "github" and "token" in config:
            if not verify_github(config["token"]):
                return Response(
                    {"detail": "Invalid GitHub Personal Access Token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            config["token"] = encrypt_credential(config["token"])

        elif source == "jira" and "token" in config:
            if not verify_jira(
                config.get("domain", obj.config.get("domain")),
                config.get("email", obj.config.get("email")),
                config["token"],
            ):
                return Response(
                    {"detail": "Invalid Jira credentials."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            config["token"] = encrypt_credential(config["token"])

        elif source == "slack" and "webhook_url" in config:
            if not verify_slack(config["webhook_url"]):
                return Response(
                    {"detail": "Invalid Slack Webhook URL."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            config["webhook_url"] = encrypt_credential(config["webhook_url"])

        # Merge new config with existing config so we don't lose old data during a partial update
        merged_config = obj.config.copy()
        merged_config.update(config)
        data["config"] = merged_config

        # 3. Save to database
        serializer = IntegrationSerializer(obj, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        integration = serializer.save()

        # 4. Automation Trigger
        if integration.source == "github" and integration.is_active:
            repositories = integration.config.get("repositories", [])
            if isinstance(repositories, str):
                repositories = [repositories]

            from .tasks import scrape_github_history

            for repo_name in repositories:
                scrape_github_history.delay(
                    repo_full_name=repo_name,
                    org_id=str(request.user.org.id),
                    user_id=str(request.user.id),
                    limit=50,
                )

        return Response(serializer.data)

    def delete(self, request, pk):
        obj = self._get_integration(pk, request.user.org)
        if not obj:
            return Response(status=status.HTTP_404_NOT_FOUND)
        obj.is_active = False
        obj.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

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


class IntegrationListCreateView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        integrations = Integration.objects.filter(org=request.user.org)
        return Response(IntegrationSerializer(integrations, many=True).data)

    def post(self, request):
        source = request.data.get("source")

        if Integration.objects.filter(org=request.user.org, source=source).exists():
            return Response(
                {
                    "detail": f"Integration for {source} already exists. Use PUT to update."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Make a mutable copy of the request data so we can modify it
        data = request.data.copy()
        config = data.get("config", {})

        # ✨ 2. VERIFICATION & ENCRYPTION BLOCK ✨
        if source == "github" and "token" in config:
            if not verify_github(config["token"]):
                return Response(
                    {"detail": "Invalid GitHub Personal Access Token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            config["token"] = encrypt_credential(config["token"])

        elif source == "jira" and "token" in config:
            if not verify_jira(
                config.get("domain"), config.get("email"), config["token"]
            ):
                return Response(
                    {"detail": "Invalid Jira credentials or domain."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            config["token"] = encrypt_credential(config["token"])

        elif source == "slack" and "webhook_url" in config:
            if not verify_slack(config["webhook_url"]):
                return Response(
                    {"detail": "Invalid Slack Webhook URL."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            config["webhook_url"] = encrypt_credential(config["webhook_url"])

        # Put the encrypted config back into the payload
        data["config"] = config

        # 3. Save to database
        serializer = IntegrationSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        integration = serializer.save(org=request.user.org)

        # 4. Automation Trigger
        if integration.source == "github" and integration.is_active:
            repositories = integration.config.get("repositories", [])
            if isinstance(repositories, str):
                repositories = [repositories]

            from .tasks import scrape_github_history

            for repo_name in repositories:
                scrape_github_history.delay(
                    repo_full_name=repo_name,
                    org_id=str(request.user.org.id),
                    user_id=str(request.user.id),
                    limit=50,
                )

        return Response(serializer.data, status=status.HTTP_201_CREATED)
