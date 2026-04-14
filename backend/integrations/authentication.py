import hashlib
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from accounts.models import APIKey


class APIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        raw_key = request.headers.get("X-API-Key")
        if not raw_key:
            return None

        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        try:
            api_key = APIKey.objects.select_related("user", "org").get(
                key_hash=key_hash, revoked_at__isnull=True
            )
        except APIKey.DoesNotExist:
            raise AuthenticationFailed("Invalid or Revoked APIKey")

        return (api_key.user, api_key)
