from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings


class TokenUser:
    """Simple user object for token-authenticated requests."""
    is_authenticated = True
    username = 'api_agent'

    def __str__(self):
        return self.username


class TokenAuthentication(BaseAuthentication):
    """Simple Bearer token authentication against XRAY_API_TOKEN setting."""

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
        elif auth_header.startswith('Token '):
            token = auth_header[6:].strip()
        else:
            # Also check query param for convenience
            token = request.query_params.get('token', '')

        if not token:
            return None  # No credentials provided — let permission class handle

        expected = getattr(settings, 'XRAY_API_TOKEN', '')
        if token != expected:
            raise AuthenticationFailed('Invalid API token.')

        return (TokenUser(), token)


class IsTokenAuthenticated(BasePermission):
    """Allow access only if authenticated via token."""

    def has_permission(self, request, view):
        return (
            request.user is not None
            and getattr(request.user, 'is_authenticated', False)
        )
