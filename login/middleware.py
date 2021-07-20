import logging
import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser

from users.models import User

logger = logging.getLogger("sc")


class JwtProviderMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def attach_anonymous_if_not_exists(self, request):
        if not hasattr(request, "user") or not request.user:
            request.user = AnonymousUser

    def authorize_jwt(self, request):
        request.jwt_success = False
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith(settings.AUTH_JWT_HEADER_PREFIX):
            self.attach_anonymous_if_not_exists(request)
            return

        header_parsed = header.split(" ")
        if len(header_parsed) == 1:
            self.attach_anonymous_if_not_exists(request)
            return

        token = header_parsed[1]

        try:
            decoded = jwt.decode(
                token, settings.AUTH_JWT_SECRET, algorithms=settings.AUTH_JWT_METHOD
            )
            user = User.objects.get(pk=decoded.get("id"))
            request.user = user
            request.token = token
            request.decoded_token = decoded
            request.jwt_success = True
        except jwt.InvalidTokenError:
            self.attach_anonymous_if_not_exists(request)
        except User.DoesNotExist:
            # logger.error(
            #    "Encountered JWT without a legitimate user: %s"
            #    % (str(decoded.get("id")),)
            # )
            self.attach_anonymous_if_not_exists(request)

        return

    def __call__(self, request):
        self.authorize_jwt(request)
        return self.get_response(request)
