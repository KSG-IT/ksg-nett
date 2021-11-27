# Generated by Django 3.2.5 on 2021-11-16 01:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0005_auto_20211116_0054"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="admission",
            name="admission_closed",
        ),
        migrations.AddField(
            model_name="admission",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", "Open"),
                    ("in-session", "In session"),
                    ("closed", "Closed"),
                ],
                default="open",
                max_length=12,
            ),
        ),
    ]
