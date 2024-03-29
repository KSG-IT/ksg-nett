# Generated by Django 3.2.16 on 2023-01-20 14:50

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0004_interview_registered_at_samfundet"),
    ]

    operations = [
        migrations.AddField(
            model_name="admission",
            name="interview_booking_late_batch_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="admission",
            name="interview_booking_override_delta",
            field=models.DurationField(default=datetime.timedelta(seconds=21600)),
        ),
        migrations.AddField(
            model_name="admission",
            name="interview_booking_override_enabled",
            field=models.BooleanField(default=False),
        ),
    ]
