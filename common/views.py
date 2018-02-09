from django.shortcuts import render, redirect
from django.urls import reverse

from internal.views import index as internal_index
from login.views import login_user


def index(request):
    """
    This view is the root index of the application. It is responsible for
    routing the requestor to the right place.

    :param request:
    :return:
    """
    if request.user.is_authenticated:
        return redirect(reverse(internal_index))
    else:
        return redirect(reverse(login_user))
