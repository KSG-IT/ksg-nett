# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.http import HttpResponse, HttpResponseRedirect
from rest_framework import status
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from users.models import User
from users.forms.user_form import UserForm

# not used anymore
def current_user(request):
    user = {'user': request.user}
    return render(request=request,
                  template_name='users/profile_page.html',
                  context=user)

# not used anymore
def edit_current_user(request):
    user = {'current_user': request.user}
    return render(request=request,
                  template_name='users/edit_profile_page.html',
                  context=user)


def get_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    ctx = {
        'user': user
    }
    return render(request, template_name='users/profile_page.html',
                  context=ctx)


def update_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    form = UserForm(request.POST or None, instance=user)
    ctx = {
        'user_form': form,
        'user': user
    }
    if request.method == "GET":
        return render(request, template_name='users/edit_profile_page.html',
                      context=ctx)
    elif request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect(reverse('user_details', kwargs={'user_id': user_id}))
        else:
            return render(request, template_name='users/edit_profile_page.html',
                          context=ctx)
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
