from django.urls import path
from . import views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    # One URL per Stripe webhook endpoint, see the STRIPE_WEBHOOK_SECRET_* settings
    path(
        "stripe-webhook",
        csrf_exempt(views.stripe_webhook),
        {"secret_setting": "STRIPE_WEBHOOK_SECRET_2022_11_15"},
    ),
    path(
        "stripe-webhook/2026-08-26",
        csrf_exempt(views.stripe_webhook),
        {"secret_setting": "STRIPE_WEBHOOK_SECRET_2026_08_26"},
    ),
    path(
        "external-charge/<str:bank_account_secret>",
        views.external_charge_view,
        name="external_charge",
    ),
    path(
        "external-charge-qr-code/<str:bank_account_secret>",
        views.external_charge_qr_code,
    ),
]
