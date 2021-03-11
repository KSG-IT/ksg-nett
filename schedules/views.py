from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.paginator import Paginator
from rest_framework import status
from django.http import HttpResponse
from django.core.exceptions import SuspiciousOperation


def schedules_home(request):
    """Renders the schedule homepage for the logged in user."""
    if request.method == "GET":
        ctx = {
        }
        return render(request, template_name="schedules/schedules_home.html", context=ctx)
    else:
        return status.HTTP_405_METHOD_NOT_ALLOWED
