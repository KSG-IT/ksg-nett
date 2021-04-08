from django.contrib import admin

from schedules.models import (
    Schedule,
    ShiftSlotGroupInterest,
    ShiftTradeOffer,
    ShiftTrade,
    ShiftSlotTemplate,
    ShiftSlotGroupDayRule,
    ShiftSlotGroupTemplate,
    ScheduleTemplate,
    Shift,
    ShiftSlot,
    ScheduleSlotType,
    ShiftSlotGroup,
)


class TemplateInlines(admin.TabularInline):
    model = ScheduleTemplate
    extra = 1


class ScheduleAdmin(admin.ModelAdmin):
    inlines = (TemplateInlines,)


class ShiftSlotGroupDayRuleInline(admin.TabularInline):
    model = ShiftSlotGroupDayRule
    extra = 1


class ShiftSlotGroupTemplateAdmin(admin.ModelAdmin):
    inlines = (ShiftSlotGroupDayRuleInline,)


class ShiftSlotInline(admin.TabularInline):
    model = ShiftSlot
    extra = 1


class ShiftSlotGroupAdmin(admin.ModelAdmin):
    inlines = (ShiftSlotInline,)


class ShiftInline(admin.TabularInline):
    model = Shift


class ShiftSlotAdmin(admin.ModelAdmin):
    pass


class ShiftAdmin(admin.ModelAdmin):
    pass


admin.site.register(Schedule, ScheduleAdmin)
admin.site.register(ShiftSlotGroup, ShiftSlotGroupAdmin)
admin.site.register(ScheduleSlotType)
admin.site.register(ShiftSlot)
admin.site.register(Shift, ShiftAdmin)
admin.site.register(ScheduleTemplate)
admin.site.register(ShiftSlotGroupTemplate, ShiftSlotGroupTemplateAdmin)
admin.site.register(ShiftSlotGroupDayRule)
admin.site.register(ShiftSlotTemplate)
admin.site.register(ShiftTrade)
admin.site.register(ShiftTradeOffer)
admin.site.register(ShiftSlotGroupInterest)
