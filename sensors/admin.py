from django.contrib import admin

# Register your models here.
from sensors.models import SensorMeasurement


class SensorMeasurementAdmin(admin.ModelAdmin):
    list_display = ["id", "type", "value", "created_at"]
    list_filter = ["type", "created_at"]
    # Counting every measurement on each page load is slow on a large table
    show_full_result_count = False


admin.site.register(SensorMeasurement, SensorMeasurementAdmin)
