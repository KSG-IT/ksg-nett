from django.conf import settings


def app_url(path):
    """
    An absolute link into the SPA. APP_URL has no scheme in dev and prod
    ("app.ksg-nett.no") but has one locally ("http://localhost:3012").
    """
    base = settings.APP_URL
    if "://" not in base:
        base = f"https://{base}"
    return base.rstrip("/") + path
