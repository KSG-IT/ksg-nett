from django.contrib import admin

from schedules.models import (
    Schedule,
    ShiftTrade,
    Shift,
    ShiftSlot,
    ScheduleTemplate,
    ShiftSlotTemplate,
    ShiftTemplate, ShiftInterest,
)


class ScheduleAdmin(admin.ModelAdmin):
    pass


class ShiftSlotInline(admin.TabularInline):
    model = ShiftSlot


class ShiftAdmin(admin.ModelAdmin):
    inlines = (ShiftSlotInline,)
    extras = 2


class ShiftSlotAdmin(admin.ModelAdmin):
    pass


class ShiftTemplateInline(admin.TabularInline):
    model = ShiftTemplate


class ScheduleTemplateAdmin(admin.ModelAdmin):
    inlines = (ShiftTemplateInline,)
    extras = 1


class ShiftSlotTemplateInline(admin.TabularInline):
    model = ShiftSlotTemplate


class ShiftTemplateAdmin(admin.ModelAdmin):
    inlines = (ShiftSlotTemplateInline,)


class ShiftSlotTemplateAdmin(admin.ModelAdmin):
    pass

class ShiftInterestAdmin(admin.ModelAdmin):
    pass


admin.site.register(Schedule, ScheduleAdmin)
admin.site.register(Shift, ShiftAdmin)
admin.site.register(ShiftTrade)
admin.site.register(ShiftSlot, ShiftSlotAdmin)
admin.site.register(ScheduleTemplate, ScheduleTemplateAdmin)
admin.site.register(ShiftTemplate, ShiftTemplateAdmin)
admin.site.register(ShiftSlotTemplate, ShiftSlotTemplateAdmin)
admin.site.register(ShiftInterest, ShiftInterestAdmin)
