from django.contrib import admin

# Register your models here.
from quotes.models import Quote, QuoteVote


class QuoteAdmin(admin.ModelAdmin):
    list_display = ["short_text", "reported_by", "approved", "created_at"]
    list_select_related = ["reported_by"]
    list_filter = ["approved", "migrated_from_sg", "created_at"]
    search_fields = [
        "text",
        "context",
        "tagged__first_name",
        "tagged__last_name",
        "tagged__nickname",
    ]
    date_hierarchy = "created_at"
    autocomplete_fields = ["tagged", "reported_by", "approved_by"]

    @admin.display(description="Text", ordering="text")
    def short_text(self, quote):
        return quote.text if len(quote.text) <= 80 else f"{quote.text[:80]}…"


class QuoteVoteAdmin(admin.ModelAdmin):
    # QuoteVote.__str__ loads the caster and every tagged user of the quote
    list_display = ["id", "quote", "caster", "value"]
    list_select_related = ["quote", "caster"]
    list_filter = ["value"]
    search_fields = ["quote__text", "caster__first_name", "caster__last_name"]
    autocomplete_fields = ["quote", "caster"]

    def get_queryset(self, request):
        # The action checkbox label renders __str__, which lists the tagged users
        return super().get_queryset(request).prefetch_related("quote__tagged")


admin.site.register(Quote, QuoteAdmin)
admin.site.register(QuoteVote, QuoteVoteAdmin)
