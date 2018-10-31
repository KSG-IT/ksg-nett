# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from users.models import User
from users.forms.user_form import UserForm


def current_user(request):
    user = {'current_user': request.user}
    return render(request=request,
                  template_name='users/profile_page.html',
                  context=user)


def edit_current_user(request):
    user = {'current_user': request.user}
    return render(request=request,
                  template_name='users/edit_profile_page.html',
                  context=user)


def update_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    form = UserForm(request.post)