from django.contrib import admin

# Register your models here.
from quotes.models import Quote, QuoteVote

admin.site.register(Quote)
admin.site.register(QuoteVote)
