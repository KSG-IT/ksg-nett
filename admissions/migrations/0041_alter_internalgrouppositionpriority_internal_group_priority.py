# Generated by Django 3.2.13 on 2022-06-16 16:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "admissions",
            "0040_alter_internalgrouppositionpriority_internal_group_priority",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="internalgrouppositionpriority",
            name="internal_group_priority",
            field=models.CharField(
                blank=True,
                choices=[
                    ("want", "Want"),
                    ("probably-want", "Probably want"),
                    ("do-not-want", "Do not want"),
                    ("reserve", "Reserve"),
                    ("currently-discussing", "Currently discussing"),
                    ("pass-around", "Pass around"),
                    ("interested", "Interested"),
                ],
                max_length=24,
                null=True,
            ),
        ),
    ]
