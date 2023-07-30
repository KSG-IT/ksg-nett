# Generated by Django 3.2.19 on 2023-07-02 21:21

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0008_interviewscheduletemplate_default_interview_notes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="admission",
            name="interview_booking_override_delta",
            field=models.DurationField(default=datetime.timedelta(seconds=10800)),
        ),
    ]