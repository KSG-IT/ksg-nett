from django.db import models

from django.utils import timezone

from sensors.consts import MEASUREMENT_TYPE_CHOICES


class SensorMeasurement(models.Model):
    type = models.CharField(
        blank=False, null=False, max_length=16, choices=MEASUREMENT_TYPE_CHOICES
    )
    value = models.FloatField(blank=False, null=False)
    created_at = models.DateTimeField(blank=False, null=False, default=timezone.now)

    def __str__(self):
        return f"{self.get_type_display()} measurement"

    class Meta:
        indexes = [
            models.Index(fields=['created_at'])
        ]
