import json

import stripe
from django.conf import settings
from django.db import transaction
from graphene_django_cud.util import disambiguate_id, disambiguate_ids
from economy.models import (
    SociProduct,
    Deposit,
)
from weasyprint import CSS, HTML

from django.template.loader import render_to_string
from users.models import User
from django.utils import timezone
from rest_framework import status
from django.http import HttpResponse, JsonResponse


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
        payment_intent_id = event["data"]["object"]["payment_intent"]

        deposit = Deposit.objects.get(stripe_payment_id=payment_intent_id)
        if not deposit.approved:
            # Already invalidated. Do nothing
            return JsonResponse(data={"success": True})

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
