import sentry_sdk
import stripe
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.shortcuts import render

from common.decorators import view_feature_flag_required
from economy.models import Deposit, SociBankAccount, ExternalCharge

from economy.utils import send_external_charge_email, send_external_charge_webhook
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from economy.forms import ExternalChargeForm
import qrcode


def deposit_for_payment_intent(payment_intent_id, event_type):
    """
    The deposit of a payment intent, locked until the transaction ends, or
    None. Call it inside transaction.atomic(). Stripe can deliver one event
    twice at the same time (two endpoints, or a retry), and the lock makes the
    second delivery wait and then see the first one's result.

    Stripe also sends events for payments that are not deposits, for example
    "Send test event" in the dashboard. Those are acknowledged so Stripe does
    not retry them.
    """
    deposit = (
        Deposit.objects.select_for_update()
        .filter(stripe_payment_id=payment_intent_id)
        .first()
    )
    if deposit is None:
        sentry_sdk.capture_message(
            f"Stripe {event_type} for payment intent {payment_intent_id} "
            "without a deposit",
            level="warning",
        )
    return deposit


def change_balance(account_id, amount):
    """Add `amount` (negative to remove) in the database, not in Python"""
    SociBankAccount.objects.filter(pk=account_id).update(balance=F("balance") + amount)


def stripe_webhook(request, secret_setting):
    """
    Each Stripe webhook endpoint has its own URL and signing secret, named after
    the API version of the endpoint. `secret_setting` comes from economy/urls.py.
    """
    payload = request.body
    sig_header = request.headers["STRIPE_SIGNATURE"]

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, getattr(settings, secret_setting)
        )
    except ValueError as e:
        # Invalid payload
        raise e
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise e

    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        intent_id = payment_intent["id"]

        with transaction.atomic():
            deposit = deposit_for_payment_intent(intent_id, event["type"])
            if deposit is None or deposit.approved:
                # Already approved. Do nothing
                return JsonResponse(data={"success": True})

            deposit.approved_at = timezone.now()
            deposit.approved = True
            deposit.save()
            change_balance(deposit.account_id, deposit.resolved_amount)

        if deposit.account.user.notify_on_deposit:
            from economy.utils import send_deposit_approved_email

            send_deposit_approved_email(deposit)

    elif event["type"] == "charge.refunded":
        event_object = event["data"]["object"]
        payment_intent_id = event_object["payment_intent"]

        with transaction.atomic():
            deposit = deposit_for_payment_intent(payment_intent_id, event["type"])
            if deposit is None or not deposit.approved:
                # Already invalidated. Do nothing
                return JsonResponse(data={"success": True})

            change_balance(deposit.account_id, -deposit.resolved_amount)
            # Could be confusing user flow if we don't delete the deposit
            deposit.delete()

        if deposit.account.user.notify_on_deposit:
            from economy.utils import send_deposit_refunded_email

            send_deposit_refunded_email(deposit)

    elif event["type"] == "payment_intent.canceled":
        intent_id = event["data"]["object"]["id"]
        # Without this the deposit stays as the ongoing intent and blocks new ones
        Deposit.objects.filter(stripe_payment_id=intent_id, approved=False).delete()

    else:
        # Stripe retries a 500 for days and can disable the endpoint, so
        # acknowledge the event and report it to Sentry instead
        sentry_sdk.capture_message(
            f"Unhandled Stripe event type {event['type']}", level="warning"
        )

    return JsonResponse(data={"success": True})


@view_feature_flag_required(settings.EXTERNAL_CHARGING_FEATURE_FLAG)
def external_charge_view(request, bank_account_secret, *args, **kwargs):
    if request.method == "POST":
        form = ExternalChargeForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "economy/external_charge.html",
                context={"form": form, "production": settings.PRODUCTION},
            )
        amount = form.cleaned_data["amount"]

        if not 0 <= amount < settings.EXTERNAL_CHARGE_MAX_AMOUNT:
            return render(
                request,
                "economy/external_charge.html",
                context={
                    "form": form,
                    "error": f"Beløpet må være større enn 0 og maks {settings.EXTERNAL_CHARGE_MAX_AMOUNT}",
                    "production": settings.PRODUCTION,
                },
            )
        bar_tab_customer = form.cleaned_data["bar_tab_customer"]
        try:
            account = SociBankAccount.objects.get(
                external_charge_secret=bank_account_secret
            )
        except SociBankAccount.DoesNotExist:
            return render(
                request,
                "economy/external_charge_error.html",
            )

        if account.balance < amount:
            return render(
                request,
                "economy/external_charge.html",
                context={
                    "form": form,
                    "error": "Det er ikke nok penger på kontoen",
                    "production": settings.PRODUCTION,
                },
            )

        reference = form.cleaned_data["reference"]

        account.remove_funds(amount)
        account.regenerate_external_charge_secret()
        ExternalCharge.objects.create(
            bank_account=account,
            amount=amount,
            bar_tab_customer=bar_tab_customer,
            reference=reference,
        )
        # ToDo: add or create a baartab and add an entry
        if account.user.notify_on_deposit:  # change to external charge flag
            send_external_charge_email(account.user, amount, bar_tab_customer)

        if bar_tab_customer.webhook_url:
            webhook_payload = {
                "amount": amount,
                "reference": reference,
                "account_name": account.user.get_full_name(),
                "source_identifier": "societeten",
            }
            send_external_charge_webhook(bar_tab_customer.webhook_url, webhook_payload)

        return render(
            request,
            "economy/external_charge_success.html",
            context={
                "amount": amount,
                "account_name": account.user.get_full_name(),
            },
        )

    elif request.method == "GET":
        account = SociBankAccount.objects.filter(
            external_charge_secret=bank_account_secret
        ).first()

        if not account:
            return render(
                request,
                "economy/external_charge_error.html",
            )

        form = ExternalChargeForm()
        ctx = {"form": form, "error": None, "production": settings.PRODUCTION}
        return render(
            request,
            "economy/external_charge.html",
            context=ctx,
        )


@view_feature_flag_required(settings.EXTERNAL_CHARGING_FEATURE_FLAG)
def external_charge_qr_code(request, bank_account_secret):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    base_url = settings.BASE_URL
    qr_data = f"{base_url}/economy/external-charge/{bank_account_secret}"
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    response = HttpResponse(content_type="image/png")
    img.save(response, "PNG")
    return response


@view_feature_flag_required(settings.EXTERNAL_CHARGING_FEATURE_FLAG)
def external_charge_webhook(request):
    if not request.method == "POST":
        return JsonResponse(
            data={
                "success": False,
                "error": "Invalid requset method. Only POST requests are allowed.",
            }
        )

    payload = request.body

    amount = payload["amount"]

    if amount <= 0:
        return JsonResponse(
            data={
                "success": False,
                "error": "Invalid amount. Amount must be greater than 0.",
            }
        )

    reference = payload["reference"]
    # Todo: Do the rest of the stuff
