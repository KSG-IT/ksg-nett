# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render


def current_user(request):
    user = {'current_user': request.user}
    return render(request=request,
                  template_name='users/profile_page.html',
                  context=user)
