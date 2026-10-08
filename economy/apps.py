from django.apps import AppConfig


class EconomyConfig(AppConfig):
    name = "economy"

    def ready(self):
        import stripe
        from django.conf import settings

        # Set once for every Stripe call. The API version is pinned here, not
        # taken from the account default in the Stripe dashboard
        stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe.api_version = settings.STRIPE_API_VERSION
