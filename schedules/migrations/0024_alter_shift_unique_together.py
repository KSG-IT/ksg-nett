# Generated by Django 3.2.13 on 2022-09-12 21:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0023_auto_20220912_2345"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="shift",
            unique_together=set(),
        ),
    ]