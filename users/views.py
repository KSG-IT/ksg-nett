# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from users.models import User


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
