from urllib.parse import urlsplit

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.template.response import TemplateResponse

from push import webpush
from push.models import PushSubscription
from push.utils import MAX_BODY_LENGTH, PushMessage, send_to_subscriptions


class TestPushForm(forms.Form):
    title = forms.CharField(max_length=100, initial="Test fra KSG-nett")
    body = forms.CharField(
        max_length=MAX_BODY_LENGTH,
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        initial="Dette er et testvarsel.",
    )
    link = forms.CharField(
        max_length=200,
        initial="/dashboard",
        help_text="A path in the app. A tap on the notification opens it.",
    )

    def clean_link(self):
        link = self.cleaned_data["link"]
        if not link.startswith("/"):
            raise forms.ValidationError("Use a path that starts with /.")
        return link

    def message(self):
        # tag "test": a new test push replaces the last one on the device
        return PushMessage(
            title=self.cleaned_data["title"],
            body=self.cleaned_data["body"],
            path=self.cleaned_data["link"],
            tag="test",
        )


def describe(result):
    """One admin message for the result of one subscription."""
    if result is None:
        return messages.ERROR, "no answer: the send crashed or hit the total timeout"
    if result.status == webpush.OK:
        return messages.SUCCESS, f"sent (status {result.status_code})"
    if result.status == webpush.GONE:
        return (
            messages.WARNING,
            f"expired (status {result.status_code}), the row is deleted",
        )
    return (
        messages.ERROR,
        f"{result.status} (status {result.status_code}): {result.reason}",
    )


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "push_service",
        "user_agent",
        "created_at",
        "last_success_at",
    )
    search_fields = ("user__first_name", "user__last_name", "user_agent")
    autocomplete_fields = ("user",)
    readonly_fields = ("vapid_public_key", "created_at", "last_success_at")
    actions = ("send_test_push",)

    @admin.display(description="Push service")
    def push_service(self, subscription):
        # The host only: the rest of the endpoint identifies the device
        return urlsplit(subscription.endpoint).hostname

    @admin.action(description="Send a test push", permissions=["change"])
    def send_test_push(self, request, queryset):
        form = TestPushForm(request.POST if "apply" in request.POST else None)
        if form.is_valid():
            if not settings.VAPID_PRIVATE_KEY:
                self.message_user(
                    request,
                    "Sending is off: VAPID_PRIVATE_KEY is empty.",
                    messages.ERROR,
                )
                return None
            subscriptions = list(queryset)
            results = send_to_subscriptions(subscriptions, form.message())
            for subscription in subscriptions:
                level, text = describe(results[subscription.pk])
                self.message_user(
                    request, f"Push subscription {subscription.pk}: {text}", level
                )
            return None

        return TemplateResponse(
            request,
            "admin/push/pushsubscription/send_test_push.html",
            {
                **self.admin_site.each_context(request),
                "title": "Send a test push",
                "opts": self.model._meta,
                "form": form,
                "subscriptions": queryset,
                "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
            },
        )
