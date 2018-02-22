# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.views import generic

from users.models import User


class CurrentUserView(generic.ListView):
    model = User
