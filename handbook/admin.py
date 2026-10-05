from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["name", "highlighted", "updated_at", "updated_by"]
    list_select_related = ["updated_by"]
    list_filter = ["highlighted"]
    search_fields = ["name", "content"]
    autocomplete_fields = ["created_by", "updated_by"]
