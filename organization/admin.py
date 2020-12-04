# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from organization.models import (
    InternalGroup,
    InternalGroupPosition,
    Commission,
    CommissionMembership,
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


class CommissionMembershipInline(admin.TabularInline):
    model = CommissionMembership
    extra = 1
    fields = ("user", "date_started", "date_ended")
    readonly_fields = ("date_started",)


class InternalGroupAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "type",
        "member_count",
    )
    inlines = (
        InternalGroupPositionsInline,
    )

    def member_count(self, obj: InternalGroup) -> int:
        return len(obj.active_members)


class InternalGroupPositionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
    )
    inlines = (
        InternalGroupPositionMembershipInline,
    )


class CommissionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "active_members"
    )

    inlines = (
        CommissionMembershipInline,
    )

    def active_members(self, obj: Commission):
        return obj.memberships.filter(date_ended__isnull=True).count()


admin.site.register(InternalGroup, InternalGroupAdmin)
admin.site.register(InternalGroupPosition, InternalGroupPositionAdmin)
admin.site.register(InternalGroupPositionMembership)
admin.site.register(Commission, CommissionAdmin)
admin.site.register(CommissionMembership)
