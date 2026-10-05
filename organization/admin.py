# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.db.models import Count, F, Q

from organization.models import (
    InternalGroup,
    InternalGroupPosition,
    InternalGroupPositionMembership,
    InternalGroupUserHighlight,
)


class InternalGroupPositionsInline(admin.TabularInline):
    model = InternalGroupPosition
    extra = 1


class InternalGroupPositionMembershipInline(admin.TabularInline):
    model = InternalGroupPositionMembership
    extra = 1
    fields = ("user", "type", "date_joined", "date_ended")
    readonly_fields = ("date_joined",)
    autocomplete_fields = ("user",)

    def get_queryset(self, request):
        # Each row prints __str__, which renders the user and the position.
        # Active memberships come first, then the most recent ones.
        return (
            super()
            .get_queryset(request)
            .select_related("user", "position")
            .order_by(F("date_ended").desc(nulls_first=True), "-date_joined")
        )


@admin.register(InternalGroup)
class InternalGroupAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "type",
        "active_members_count",
    )
    list_filter = ("type",)
    search_fields = ("name",)
    inlines = (InternalGroupPositionsInline,)

    def get_queryset(self, request):
        # The model property loads every membership and its user for each group
        return (
            super()
            .get_queryset(request)
            .annotate(
                active_member_total=Count(
                    "positions__memberships",
                    filter=Q(positions__memberships__date_ended__isnull=True),
                )
            )
        )

    @admin.display(description="Active members", ordering="active_member_total")
    def active_members_count(self, internal_group):
        return internal_group.active_member_total


@admin.register(InternalGroupPosition)
class InternalGroupPositionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "internal_group",
        "available_externally",
        "active_memberships_count",
    )
    list_filter = ("internal_group", "available_externally")
    search_fields = ("name", "internal_group__name")
    inlines = (InternalGroupPositionMembershipInline,)

    def get_queryset(self, request):
        # __str__ renders the internal group, also in autocomplete results
        return (
            super()
            .get_queryset(request)
            .select_related("internal_group")
            .annotate(
                active_member_total=Count(
                    "memberships", filter=Q(memberships__date_ended__isnull=True)
                )
            )
        )

    @admin.display(description="Active members", ordering="active_member_total")
    def active_memberships_count(self, position):
        return position.active_member_total


@admin.register(InternalGroupPositionMembership)
class InternalGroupPositionMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "position", "type", "date_joined", "date_ended")
    list_select_related = ("user", "position__internal_group")
    list_filter = (
        ("date_ended", admin.EmptyFieldListFilter),
        "type",
        "position__internal_group",
    )
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "position__name",
        "position__internal_group__name",
    )
    autocomplete_fields = ("user", "position")


@admin.register(InternalGroupUserHighlight)
class InternalGroupUserHightlightAdmin(admin.ModelAdmin):
    list_display = ("user", "internal_group", "occupation", "archived", "image")
    list_select_related = ("user", "internal_group")
    list_filter = ("internal_group", "archived")
    search_fields = ("user__first_name", "user__last_name", "occupation")
    autocomplete_fields = ("user",)
