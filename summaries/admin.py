from django.contrib import admin

# Register your models here.
from summaries.models import Summary


class SummaryAdmin(admin.ModelAdmin):
    search_fields = (
        "contents",
        "title",
    )
    filter_horizontal = ("participants",)


admin.site.register(Summary, SummaryAdmin)
