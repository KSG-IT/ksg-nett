from django.contrib import admin

from events.models import Event


class EventAdmin(admin.ModelAdmin):
    filter_horizontal = ('participants', 'allowed_to_join',)
    pass


admin.site.register(Event, EventAdmin)
