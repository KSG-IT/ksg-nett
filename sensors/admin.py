from django.contrib import admin

# Register your models here.
from sensors.models import SensorMeasurement

admin.site.register(SensorMeasurement)
