# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, HttpResponse, redirect
from rest_framework import status
from users.models import User
from users.forms.user_form import UserForm
from django.urls import reverse


def current_user(request):
    user = {'current_user': request.user}
    return render(request=request,
                  template_name='users/profile_page.html',
                  context=user)


@login_required
def user_detail(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    ctx = {
        # We don't want to name it `user` as it will override the default user attribute
        # (which is the user calling the view).
        'profile_user': user
    }
    return render(request, template_name='users/profile_page.html', context=ctx)


@login_required(login_url='/login/')
def update_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    form = UserForm(request.POST or None, instance=user)
    ctx = {
        'user_form': form,
        'profile_user': user
    }
    if request.method == "GET":
        return render(request, template_name='users/update_profile_page.html',
                      context=ctx)
    elif request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect(reverse('user_detail', kwargs={'user_id': user_id}))
        else:
            return render(request, template_name='users/update_profile_page.html',
                          context=ctx)
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
