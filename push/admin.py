from django.contrib import admin

from push.models import PushSubscription


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "user_agent", "created_at", "last_success_at")
    search_fields = ("user__first_name", "user__last_name", "user_agent")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "last_success_at")
