from django.contrib import admin

from schedules.models import (
    Schedule,
    ShiftTrade,
    Shift,
    ShiftSlot,
    ScheduleTemplate,
    ShiftSlotTemplate,
    ShiftTemplate,
    ShiftInterest,
    ScheduleRoster,
    ScheduleRosterGrouping,
)

USER_SEARCH_FIELDS = ("user__username", "user__first_name", "user__last_name")


class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("name", "internal_group", "display_mode", "default_role")
    list_filter = ("internal_group",)
    search_fields = ("name",)


class ShiftSlotInline(admin.TabularInline):
    model = ShiftSlot
    autocomplete_fields = ("user",)


class ShiftAdmin(admin.ModelAdmin):
    list_display = ("name", "schedule", "location", "datetime_start", "datetime_end")
    list_filter = ("schedule", "location", "datetime_start")
    search_fields = ("name", "schedule__name")
    date_hierarchy = "datetime_start"
    inlines = (ShiftSlotInline,)
    extras = 2

    def get_queryset(self, request):
        # __str__ renders the schedule, also in autocomplete results. A
        # select_related() here makes the changelist ignore list_select_related.
        return super().get_queryset(request).select_related("schedule")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # ScheduleTemplate.__str__ renders the schedule
        if db_field.name == "generated_from":
            kwargs["queryset"] = ScheduleTemplate.objects.select_related("schedule")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ShiftSlotAdmin(admin.ModelAdmin):
    list_display = ("id", "shift", "role", "user")
    list_select_related = ("shift__schedule", "user")
    list_filter = ("role", "shift__schedule")
    search_fields = USER_SEARCH_FIELDS + ("shift__name",)
    date_hierarchy = "shift__datetime_start"
    autocomplete_fields = ("shift", "user")


class ShiftTradeAdmin(admin.ModelAdmin):
    list_display = ("id", "shift", "status", "offeror", "taker", "verified_by")
    list_select_related = ("shift__schedule", "offeror", "taker", "verified_by")
    list_filter = ("status",)
    search_fields = (
        "offeror__first_name",
        "offeror__last_name",
        "taker__first_name",
        "taker__last_name",
    )
    autocomplete_fields = ("shift", "offeror", "taker", "verified_by")


class ShiftTemplateInline(admin.TabularInline):
    model = ShiftTemplate


class ScheduleTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "schedule")
    list_select_related = ("schedule",)
    list_filter = ("schedule",)
    search_fields = ("name", "schedule__name")
    inlines = (ShiftTemplateInline,)
    extras = 1


class ShiftSlotTemplateInline(admin.TabularInline):
    model = ShiftSlotTemplate


class ShiftTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "schedule_template",
        "day",
        "time_start",
        "time_end",
        "location",
    )
    list_select_related = ("schedule_template__schedule",)
    list_filter = ("schedule_template__schedule", "day", "location")
    search_fields = ("name",)
    inlines = (ShiftSlotTemplateInline,)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # ScheduleTemplate.__str__ renders the schedule
        if db_field.name == "schedule_template":
            kwargs["queryset"] = ScheduleTemplate.objects.select_related("schedule")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ShiftSlotTemplateAdmin(admin.ModelAdmin):
    list_display = ("shift_template", "role", "count")
    list_select_related = ("shift_template__schedule_template",)
    list_filter = ("role", "shift_template__schedule_template__schedule")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # ShiftTemplate.__str__ renders the schedule template
        if db_field.name == "shift_template":
            kwargs["queryset"] = ShiftTemplate.objects.select_related(
                "schedule_template"
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ShiftInterestAdmin(admin.ModelAdmin):
    list_display = ("id", "shift", "user", "interest_type", "created_at")
    list_select_related = ("shift__schedule", "user")
    list_filter = ("interest_type", "shift__schedule")
    search_fields = USER_SEARCH_FIELDS + ("shift__name",)
    autocomplete_fields = ("shift", "user")


class ScheduleRosterAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "schedule",
        "user",
        "autofill_as",
        "default_availability",
        "shift_cap",
        "manually_edited",
        "added_manually",
    )
    list_select_related = ("schedule", "user")
    list_filter = ("schedule", "autofill_as", "default_availability")
    search_fields = USER_SEARCH_FIELDS
    autocomplete_fields = ("user",)


admin.site.register(Schedule, ScheduleAdmin)
admin.site.register(Shift, ShiftAdmin)
admin.site.register(ShiftTrade, ShiftTradeAdmin)
admin.site.register(ShiftSlot, ShiftSlotAdmin)
admin.site.register(ScheduleTemplate, ScheduleTemplateAdmin)
admin.site.register(ShiftTemplate, ShiftTemplateAdmin)
admin.site.register(ShiftSlotTemplate, ShiftSlotTemplateAdmin)
admin.site.register(ShiftInterest, ShiftInterestAdmin)
admin.site.register(ScheduleRoster, ScheduleRosterAdmin)


class ScheduleRosterGroupingAdmin(admin.ModelAdmin):
    list_display = (
        "schedule",
        "internal_group_position",
        "position_type",
        "role",
        "default_availability",
        "shift_cap",
    )
    list_select_related = ("schedule", "internal_group_position")
    list_filter = ("schedule",)


admin.site.register(ScheduleRosterGrouping, ScheduleRosterGroupingAdmin)
