import json
import logging
from concurrent.futures import ThreadPoolExecutor, wait
from urllib.parse import urlsplit

from django.conf import settings
from django.utils import timezone

from push import webpush
from push.models import PushSubscription

logger = logging.getLogger(__name__)

# A push that waits longer than a day at the push service is old news
PUSH_TTL = 24 * 60 * 60


# The push services of the browsers we support. The server posts to the
# endpoint a browser gives, so any other host is refused (no SSRF).
PUSH_SERVICE_DOMAINS = (
    "fcm.googleapis.com",  # Chrome, Edge on Android, Samsung Internet, Opera
    "push.apple.com",  # Safari, iOS
    "push.services.mozilla.com",  # Firefox
    "notify.windows.com",  # Edge on Windows
)


def is_push_service_endpoint(endpoint):
    try:
        parts = urlsplit(endpoint)
        port = parts.port
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    return (
        parts.scheme == "https"
        and port is None
        and any(
            host == domain or host.endswith(f".{domain}")
            for domain in PUSH_SERVICE_DOMAINS
        )
    )


def app_url(path):
    """
    An absolute link into the SPA. APP_URL has no scheme in dev and prod
    ("app.ksg-nett.no") but has one locally ("http://localhost:3012").
    """
    base = settings.APP_URL
    if "://" not in base:
        base = f"https://{base}"
    return base.rstrip("/") + path


def send_to_users(user_ids, payload, topic=None, urgency="normal"):
    """
    Push `payload` (a dict, sent as JSON) to every device of the users. Sends
    in parallel and waits at most PUSH_TOTAL_TIMEOUT. Never raises, so a
    failed push never fails the request that triggered it.
    """
    try:
        _send_to_users(user_ids, payload, topic, urgency)
    except Exception:
        # Error level, so Sentry gets it
        logger.exception("Push to users failed")


def _send_to_users(user_ids, payload, topic, urgency):
    if not settings.VAPID_PRIVATE_KEY:
        return
    subscriptions = list(PushSubscription.objects.filter(user_id__in=user_ids))
    if not subscriptions:
        return
    key = webpush.load_vapid_key(settings.VAPID_PRIVATE_KEY)
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    subject = f"mailto:{settings.VAPID_CONTACT_EMAIL}"

    # The workers only make HTTP calls. They read fields that are already
    # loaded and never touch the ORM.
    pool = ThreadPoolExecutor(
        max_workers=min(settings.PUSH_MAX_WORKERS, len(subscriptions))
    )
    futures = {
        pool.submit(
            webpush.send,
            subscription,
            body,
            key,
            subject,
            ttl=PUSH_TTL,
            urgency=urgency,
            topic=topic,
            timeout=settings.PUSH_REQUEST_TIMEOUT,
        ): subscription
        for subscription in subscriptions
    }
    done, not_done = wait(futures, timeout=settings.PUSH_TOTAL_TIMEOUT)
    # Sends still running are left behind; their own timeout ends them
    pool.shutdown(wait=False, cancel_futures=True)
    if not_done:
        logger.warning(
            "Push total timeout cut off %d of %d sends", len(not_done), len(futures)
        )

    ok, gone = [], []
    for future in done:
        subscription = futures[future]
        try:
            result = future.result()
        except Exception:
            logger.exception("Push to subscription %s failed", subscription.pk)
            continue
        if result.status == webpush.OK:
            ok.append(subscription.pk)
        elif result.status == webpush.GONE:
            gone.append(subscription.pk)
        elif result.status == webpush.RETRY_LATER:
            logger.warning(
                "Push to subscription %s: retry later (status %s)",
                subscription.pk,
                result.status_code,
            )
        else:
            # Usually a wrong VAPID key, aud or sub, or a payload too large
            logger.error(
                "Push to subscription %s: %s (status %s)",
                subscription.pk,
                result.status,
                result.status_code,
            )

    if gone:
        PushSubscription.objects.filter(pk__in=gone).delete()
    if ok:
        PushSubscription.objects.filter(pk__in=ok).update(
            last_success_at=timezone.now()
        )
