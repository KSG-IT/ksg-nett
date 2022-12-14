# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from organization.models import (
    InternalGroup,
    InternalGroupPosition,
    InternalGroupPositionMembership,
)


class InternalGroupPositionsInline(admin.TabularInline):
    model = InternalGroupPosition
    extra = 1


class InternalGroupPositionMembershipInline(admin.TabularInline):
    model = InternalGroupPositionMembership
    extra = 1
    fields = ("user", "date_joined", "date_ended")
    readonly_fields = ("date_joined",)


class InternalGroupAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "active_members_count",
    )
    inlines = (InternalGroupPositionsInline,)


class InternalGroupPositionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "internal_group",
        "active_memberships_count",
    )
    inlines = (InternalGroupPositionMembershipInline,)


admin.site.register(InternalGroup, InternalGroupAdmin)
admin.site.register(InternalGroupPosition, InternalGroupPositionAdmin)
admin.site.register(InternalGroupPositionMembership)
