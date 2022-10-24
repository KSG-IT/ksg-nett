from django.contrib import admin

# Register your models here.
from summaries.models import Summary, LegacySummary

admin.site.register(Summary)
admin.site.register(LegacySummary)
