# Generated by Django 3.2.18 on 2023-04-20 21:54

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organization", "0003_auto_20230110_1123"),
    ]

    operations = [
        migrations.CreateModel(
            name="Event",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField()),
                ("datetime_start", models.DateTimeField()),
                ("datetime_end", models.DateTimeField(blank=True, null=True)),
                (
                    "datetime_registration_start",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("location", models.CharField(blank=True, max_length=255, null=True)),
                ("max_participants", models.IntegerField(blank=True, null=True)),
                (
                    "invited_internal_groups",
                    models.ManyToManyField(
                        blank=True,
                        related_name="available_events",
                        to="organization.InternalGroup",
                    ),
                ),
                (
                    "participants",
                    models.ManyToManyField(
                        blank=True,
                        related_name="events_attending",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Event",
                "verbose_name_plural": "Events",
                "ordering": ["datetime_start"],
            },
        ),
        migrations.CreateModel(
            name="WaitListUser",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("datetime_joined", models.DateTimeField(auto_now_add=True)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="events.event"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("user", "event")},
            },
        ),
        migrations.AddField(
            model_name="event",
            name="wait_list",
            field=models.ManyToManyField(
                blank=True,
                related_name="events_on_wait_list",
                through="events.WaitListUser",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
