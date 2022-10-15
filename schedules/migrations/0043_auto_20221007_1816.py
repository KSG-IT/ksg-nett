# Generated by Django 3.2.14 on 2022-10-07 16:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0042_shift_generated_from"),
    ]

    operations = [
        migrations.AlterField(
            model_name="shiftslot",
            name="role",
            field=models.CharField(
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
                    ("BAREVAKT", "Bærevakt"),
                    ("SOCIVAKT", "Socivakt"),
                ],
                max_length=64,
            ),
        ),
        migrations.AlterField(
            model_name="shiftslottemplate",
            name="role",
            field=models.CharField(
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
                    ("BAREVAKT", "Bærevakt"),
                    ("SOCIVAKT", "Socivakt"),
                ],
                max_length=64,
            ),
        ),
    ]