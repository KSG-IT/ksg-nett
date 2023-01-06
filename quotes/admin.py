from django.contrib import admin

# Register your models here.
from quotes.models import Quote, QuoteVote


class QuoteAdmin(admin.ModelAdmin):
    search_fields = ["text", "context"]


admin.site.register(Quote, QuoteAdmin)
admin.site.register(QuoteVote)
