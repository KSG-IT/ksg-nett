import json

from django.conf import settings
from graphene_django_cud.util import disambiguate_id, disambiguate_ids

from economy.forms import DepositForm, DepositCommentForm, ProductOrderForm
from economy.models import (
    Deposit,
    DepositComment,
    SociBankAccount,
    SociSession,
    SociProduct,
    ProductOrder,
)
from weasyprint import CSS, HTML
import csv
from io import BytesIO
from typing import Iterable, Tuple, List, Any
from zoneinfo import ZoneInfo

import dateutil
import dateutil.parser as parser
from datetime import datetime

from django.http import HttpResponse
from django.template.loader import render_to_string
from users.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.paginator import Paginator
import datetime
from django.utils import timezone
from rest_framework import status
from django.http import HttpResponse
from django.core.exceptions import SuspiciousOperation


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
    print(request.POST)
    user_ids = json.loads(request.POST.getlist("user_ids")[0])
    product_ids = json.loads(request.POST.getlist("product_ids")[0])
    printed_by = request.POST.get("printed_by")
    print(product_ids)
    user_ids = disambiguate_ids(user_ids)
    product_ids = disambiguate_ids(product_ids)

    print(user_ids)
    print(product_ids)
    users = User.objects.filter(id__in=user_ids).order_by("first_name")
    products = SociProduct.objects.filter(id__in=product_ids)
    printed_by = User.objects.get(id=disambiguate_id(printed_by))
    print(users)
    print(products)
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
