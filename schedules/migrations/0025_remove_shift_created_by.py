# Generated by Django 3.2.13 on 2022-09-12 22:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0024_alter_shift_unique_together"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="shift",
            name="created_by",
        ),
    ]
