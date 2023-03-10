import json

import stripe
from django.conf import settings
from django.db import transaction
from django.shortcuts import render
from graphene_django_cud.util import disambiguate_id, disambiguate_ids

from common.decorators import view_feature_flag_required
from economy.models import SociProduct, Deposit, SociBankAccount, ExternalCharge
from weasyprint import CSS, HTML

from django.template.loader import render_to_string

from economy.utils import send_external_charge_email, send_external_charge_webhook
from users.models import User
from django.utils import timezone
from rest_framework import status
from django.http import HttpResponse, JsonResponse
from economy.forms import ExternalChargeForm
import qrcode


def generate_pdf_response_from_template(context, file_name, template_name):
    html_content = render_to_string(template_name=template_name, context=context)
    css = CSS(string="")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"inline; filename={file_name}"

    HTML(string=html_content, base_url=settings.BASE_URL).write_pdf(
        response, stylesheets=[css]
    )
    return response


def download_soci_session_list_pdf(request):
    if request.method == "GET":
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    # get user_ids and product_ids from request
    user_ids = json.loads(request.POST.getlist("user_ids")[0])
    product_ids = json.loads(request.POST.getlist("product_ids")[0])
    printed_by = request.POST.get("printed_by")
    user_ids = disambiguate_ids(user_ids)
    product_ids = disambiguate_ids(product_ids)

    users = User.objects.filter(id__in=user_ids).order_by("first_name")
    products = SociProduct.objects.filter(id__in=product_ids)
    printed_by = User.objects.get(id=disambiguate_id(printed_by))
    ctx = {
        "users": users,
        "products": products,
        "printed_by": printed_by,
        "timestamp": timezone.now(),
    }
    res = generate_pdf_response_from_template(
        ctx, "Krysselist.pdf", "economy/soci_session_list.html"
    )
    return res


def stripe_webhook(request):
    payload = request.body
    sig_header = request.headers["STRIPE_SIGNATURE"]

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
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
        deposit = Deposit.objects.get(stripe_payment_id=intent_id)
        if deposit.approved:
            # Already approved. Do nothing
            return JsonResponse(data={"success": True})

        with transaction.atomic():
            from economy.utils import send_deposit_approved_email

            deposit.approved_at = timezone.now()
            deposit.approved = True
            deposit.save()
            deposit.account.add_funds(deposit.resolved_amount)
            if deposit.account.user.notify_on_deposit:
                send_deposit_approved_email(deposit)

    elif event["type"] == "charge.refunded":
        event_object = event["data"]["object"]
        payment_intent_id = event_object["payment_intent"]

        deposit = Deposit.objects.get(stripe_payment_id=payment_intent_id)

        if not deposit.approved:
            # Already invalidated. Do nothing
            return JsonResponse(data={"success": True})

        amount_captured = event_object["amount_captured"]
        amount_refunded = event_object["amount_refunded"]
        amount = event_object["amount"]

        calculated_fee = deposit.amount - deposit.resolved_amount

        with transaction.atomic():
            from economy.utils import send_deposit_refunded_email

            deposit.approved = False
            deposit.account.remove_funds(deposit.resolved_amount)
            deposit.save()
            if deposit.account.user.notify_on_deposit:
                send_deposit_refunded_email(deposit)
                # Could be confusing user flow if we don't delete the deposit
                deposit.delete()
    else:
        raise Exception(f"Unhandled event type {event['type']}")

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
