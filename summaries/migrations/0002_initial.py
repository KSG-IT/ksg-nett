# Generated by Django 3.2.16 on 2023-01-03 15:12

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("summaries", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="summary",
            name="participants",
            field=models.ManyToManyField(
                blank=True,
                related_name="meetings_attended_summaries",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="summary",
            name="reporter",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reported_summaries",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
