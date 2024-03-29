# Generated by Django 3.2.16 on 2023-01-03 15:12

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Schedule",
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
                ("name", models.CharField(max_length=100, unique=True)),
                (
                    "display_mode",
                    models.CharField(
                        choices=[
                            ("SINGLE_LOCATION", "Single location"),
                            ("MULTIPLE_LOCATIONS", "Multiple locations"),
                        ],
                        default="SINGLE_LOCATION",
                        max_length=20,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "schedules",
            },
        ),
        migrations.CreateModel(
            name="ScheduleTemplate",
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
                ("name", models.CharField(max_length=100)),
            ],
            options={
                "verbose_name_plural": "schedule templates",
            },
        ),
        migrations.CreateModel(
            name="Shift",
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
                ("name", models.CharField(max_length=69)),
                (
                    "location",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("EDGAR", "Edgar"),
                            ("BODEGAEN", "Bodegaen"),
                            ("RUNDHALLEN", "Rundhallen"),
                            ("KLUBBEN", "Klubben"),
                            ("LYCHE_BAR", "Lyche Bar"),
                            ("LYCHE_KJOKKEN", "Lyche Kjøkken"),
                            ("STORSALEN", "Storsalen"),
                            ("SELSKAPSSIDEN", "Selskapssiden"),
                            ("STROSSA", "Strossa"),
                            ("DAGLIGHALLEN_BAR", "Daglighallen Bar"),
                        ],
                        max_length=64,
                        null=True,
                    ),
                ),
                ("datetime_start", models.DateTimeField()),
                ("datetime_end", models.DateTimeField()),
            ],
            options={
                "verbose_name_plural": "shifts",
            },
        ),
        migrations.CreateModel(
            name="ShiftSlot",
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
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("BARISTA", "Barista"),
                            ("KAFEANSVARLIG", "Kaféansvarlig"),
                            ("BARSERVITOR", "Barservitør"),
                            ("HOVMESTER", "Hovmester"),
                            ("KOKK", "Kokk"),
                            ("SOUSCHEF", "Souschef"),
                            ("ARRANGEMENTBARTENDER", "Arrangementbartender"),
                            ("ARRANGEMENTANSVARLIG", "Arrangementansvarlig"),
                            ("BRYGGER", "Brygger"),
                            ("BARTENDER", "Bartender"),
                            ("BARSJEF", "Barsjef"),
                            ("SPRITBARTENDER", "Spritbartender"),
                            ("SPRITBARSJEF", "Spritbarsjef"),
                            ("UGLE", "Ugle"),
                            ("BRANNVAKT", "Brannvakt"),
                            ("RYDDEVAKT", "Ryddevakt"),
                            ("BAEREVAKT", "Bærevakt"),
                            ("SOCIVAKT", "Socivakt"),
                        ],
                        max_length=64,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Shift slots",
            },
        ),
        migrations.CreateModel(
            name="ShiftSlotTemplate",
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
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("BARISTA", "Barista"),
                            ("KAFEANSVARLIG", "Kaféansvarlig"),
                            ("BARSERVITOR", "Barservitør"),
                            ("HOVMESTER", "Hovmester"),
                            ("KOKK", "Kokk"),
                            ("SOUSCHEF", "Souschef"),
                            ("ARRANGEMENTBARTENDER", "Arrangementbartender"),
                            ("ARRANGEMENTANSVARLIG", "Arrangementansvarlig"),
                            ("BRYGGER", "Brygger"),
                            ("BARTENDER", "Bartender"),
                            ("BARSJEF", "Barsjef"),
                            ("SPRITBARTENDER", "Spritbartender"),
                            ("SPRITBARSJEF", "Spritbarsjef"),
                            ("UGLE", "Ugle"),
                            ("BRANNVAKT", "Brannvakt"),
                            ("RYDDEVAKT", "Ryddevakt"),
                            ("BAEREVAKT", "Bærevakt"),
                            ("SOCIVAKT", "Socivakt"),
                        ],
                        max_length=64,
                    ),
                ),
                ("count", models.IntegerField()),
            ],
            options={
                "verbose_name_plural": "Shift slot templates",
            },
        ),
        migrations.CreateModel(
            name="ShiftTemplate",
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
                (
                    "name",
                    models.CharField(
                        help_text="Name that will be applied to the generated shift",
                        max_length=100,
                    ),
                ),
                (
                    "location",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("EDGAR", "Edgar"),
                            ("BODEGAEN", "Bodegaen"),
                            ("RUNDHALLEN", "Rundhallen"),
                            ("KLUBBEN", "Klubben"),
                            ("LYCHE_BAR", "Lyche Bar"),
                            ("LYCHE_KJOKKEN", "Lyche Kjøkken"),
                            ("STORSALEN", "Storsalen"),
                            ("SELSKAPSSIDEN", "Selskapssiden"),
                            ("STROSSA", "Strossa"),
                            ("DAGLIGHALLEN_BAR", "Daglighallen Bar"),
                        ],
                        max_length=64,
                        null=True,
                    ),
                ),
                (
                    "day",
                    models.CharField(
                        choices=[
                            ("MONDAY", "Monday"),
                            ("TUESDAY", "Tuesday"),
                            ("WEDNESDAY", "Wednesday"),
                            ("THURSDAY", "Thursday"),
                            ("FRIDAY", "Friday"),
                            ("SATURDAY", "Saturday"),
                            ("SUNDAY", "Sunday"),
                        ],
                        help_text="Day of the week this shift occurs",
                        max_length=32,
                    ),
                ),
                ("time_start", models.TimeField()),
                ("time_end", models.TimeField()),
            ],
            options={
                "verbose_name_plural": "Shift templates",
            },
        ),
        migrations.CreateModel(
            name="ShiftTrade",
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
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("OFFERED", "Offered"),
                            ("REQUESTED", "Requested"),
                            ("COMPLETE", "Complete"),
                        ],
                        default="OFFERED",
                        max_length=32,
                    ),
                ),
            ],
        ),
    ]
