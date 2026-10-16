from django.contrib import admin

from chat.models import Chat, ChatMembership, ChatMessage


class ChatMembershipInline(admin.TabularInline):
    model = ChatMembership
    extra = 0
    autocomplete_fields = ("user",)
    exclude = ("last_read_message",)


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "created_by",
        "created_at",
        "closes_at",
        "last_message_at",
        "members_editable",
    )
    search_fields = ("name",)
    autocomplete_fields = ("created_by",)
    inlines = (ChatMembershipInline,)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("chat", "sender", "role", "created_at", "hidden_at")
    list_filter = ("role",)
    search_fields = ("body", "chat__name")
    autocomplete_fields = ("chat", "sender", "hidden_by")
