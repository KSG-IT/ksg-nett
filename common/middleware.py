import json
import logging
import time
import uuid

from django.conf import settings

logger = logging.getLogger("ksg_nett.requests")

# Only JSON bodies up to this size are read, to find the GraphQL operation name.
MAX_BODY_TO_PARSE = 100_000


def request_id(request):
    """
    Varnish adds X-Varnish (its request id, the same number as in varnishlog)
    to each request it sends to the backend. Use it, so the Django log line
    can be matched to the Varnish log. Otherwise make a short random id.
    """
    varnish_id = request.META.get("HTTP_X_VARNISH", "").split(" ")[0]
    if varnish_id.isdigit():
        return varnish_id
    return uuid.uuid4().hex[:12]


def operation_name(request):
    """
    The GraphQL operation name, from ?op= or from a JSON body. Never reads a
    multipart body (file uploads): Django could then not parse request.POST.
    """
    if request.GET.get("op"):
        return request.GET["op"]

    content_type = request.META.get("CONTENT_TYPE", "")
    content_length = int(request.META.get("CONTENT_LENGTH") or 0)
    if not content_type.startswith("application/json"):
        return None
    if not 0 < content_length <= MAX_BODY_TO_PARSE:
        return None
    try:
        name = json.loads(request.body).get("operationName")
    except (ValueError, AttributeError):
        return None
    return name if isinstance(name, str) else None


class RequestLogMiddleware:
    """
    One log line per request: request id, method, path, GraphQL operation,
    user id, status, sizes and duration. Never the body, variables or tokens.

    The line is DEBUG, so it shows only with LOG_LEVEL=DEBUG. A server error
    (5xx) or a request that takes REQUEST_LOG_SLOW_MS or more is always a
    WARNING.
    The response gets the request id as X-Request-ID.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rid = request_id(request)
        operation = operation_name(request)
        started = time.monotonic()

        response = self.get_response(request)

        duration_ms = round((time.monotonic() - started) * 1000)
        response["X-Request-ID"] = rid

        user = getattr(request, "user", None)
        user_id = user.id if user is not None and user.is_authenticated else "anon"
        size = (
            len(response.content)
            if not getattr(response, "streaming", False)
            else "stream"
        )
        slow = duration_ms >= getattr(settings, "REQUEST_LOG_SLOW_MS", 2000)
        level = (
            logging.WARNING if response.status_code >= 500 or slow else logging.DEBUG
        )

        logger.log(
            level,
            "rid=%s %s %s op=%s user=%s status=%s req=%sB resp=%sB ms=%s",
            rid,
            request.method,
            request.path,
            operation or "-",
            user_id,
            response.status_code,
            request.META.get("CONTENT_LENGTH") or 0,
            size,
            duration_ms,
        )
        return response
