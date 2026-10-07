from django.conf import settings
from rest_framework import permissions
from rest_framework.request import Request

from common.util import check_feature_flag


class SensorTokenPermission(permissions.BasePermission):
    def has_permission(self, request: Request, view):
        if not "HTTP_AUTHORIZATION" in request.META:
            return False

        bearer_token: str = request.META["HTTP_AUTHORIZATION"].replace("Bearer ", "")
        return bearer_token == settings.SENSOR_API_TOKEN


class XAppAuthPermission(permissions.BasePermission):
    """
    Lets any request through while the X-App auth feature flag is off.
    When it is on, the request needs the JWT from obtain-token.
    """

    def has_permission(self, request: Request, view):
        if not check_feature_flag(
            settings.X_APP_REQUIRE_AUTH_FEATURE_FLAG, fail_silently=True
        ):
            return True

        return bool(request.user and request.user.is_authenticated)
