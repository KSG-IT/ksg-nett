from django.contrib import admin

# Register your models here.
from summaries.models import Summary


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
