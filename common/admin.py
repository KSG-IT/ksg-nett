from django.contrib import admin
from .models import FeatureFlag


class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ["name", "enabled", "description"]
    list_filter = ["enabled"]
    search_fields = ["name", "description"]


admin.site.register(FeatureFlag, FeatureFlagAdmin)
