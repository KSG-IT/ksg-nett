from django.contrib import admin
from django.forms import ModelForm

from organization.models import InternalGroupPosition
from schedules.models import (
    Schedule,
    ShiftTrade,
    Shift,
    ScheduleSlotType,
)

class ScheduleAdmin(admin.ModelAdmin):
    pass


class ShiftInline(admin.TabularInline):
    model = Shift


class ShiftSlotAdmin(admin.ModelAdmin):
    inlines = (ShiftInline,)


class ShiftAdmin(admin.ModelAdmin):
    pass


class RequiredRoleInline(admin.TabularInline):
    model = InternalGroupPosition
    extra = 4






admin.site.register(Schedule, ScheduleAdmin)
admin.site.register(ScheduleSlotType)
admin.site.register(Shift, ShiftAdmin)
admin.site.register(ShiftTrade)
