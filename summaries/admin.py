from django.contrib import admin

# Register your models here.
from summaries.models import Summary, SummaryReadReceipt


class SummaryAdmin(admin.ModelAdmin):
    list_display = ("date", "internal_group", "title", "reporter")
    list_select_related = ("internal_group", "reporter")
    list_filter = ("internal_group",)
    search_fields = (
        "contents",
        "title",
    )
    date_hierarchy = "date"
    filter_horizontal = ("participants",)
    autocomplete_fields = ("reporter",)


admin.site.register(Summary, SummaryAdmin)


class SummaryReadReceiptAdmin(admin.ModelAdmin):
    list_display = ("summary", "user", "opened_at", "read_at")
    list_select_related = ("summary", "summary__internal_group", "user")
    list_filter = ("summary__internal_group",)
    date_hierarchy = "opened_at"
    autocomplete_fields = ("summary", "user")


admin.site.register(SummaryReadReceipt, SummaryReadReceiptAdmin)
