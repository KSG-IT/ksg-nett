from django.contrib import admin

from schedules.models import Schedule, ShiftSlotGroupInterest, ShiftTradeOffer, ShiftTrade, ShiftSlotTemplate, \
    ShiftSlotDayRule, ShiftSlotGroupTemplate, ScheduleTemplate, Shift, ShiftSlot, ScheduleSlotType, ShiftSlotGroup

admin.site.register(Schedule)
admin.site.register(ShiftSlotGroup)
admin.site.register(ScheduleSlotType)
admin.site.register(ShiftSlot)
admin.site.register(Shift)
admin.site.register(ScheduleTemplate)
admin.site.register(ShiftSlotGroupTemplate)
admin.site.register(ShiftSlotDayRule)
admin.site.register(ShiftSlotTemplate)
admin.site.register(ShiftTrade)
admin.site.register(ShiftTradeOffer)
admin.site.register(ShiftSlotGroupInterest)
