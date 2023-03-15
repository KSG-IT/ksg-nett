from django.urls import path
from . import views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path("stripe-webhook", csrf_exempt(views.stripe_webhook)),
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
