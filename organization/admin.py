# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from organization.models import InternalGroup, InternalGroupPosition

admin.site.register(InternalGroup)
admin.site.register(InternalGroupPosition)
