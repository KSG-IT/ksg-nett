from django.conf import settings
from rest_framework import permissions
from rest_framework.request import Request


class SensorTokenPermission(permissions.BasePermission):
    def has_permission(self, request: Request, view):
        if not 'HTTP_AUTHORIZATION' in request.META:
            return False

        bearer_token: str = request.META['HTTP_AUTHORIZATION'].replace("Bearer ", "")
        return bearer_token == settings.SENSOR_API_TOKEN
