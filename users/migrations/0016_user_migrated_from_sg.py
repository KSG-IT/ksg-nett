# Generated by Django 3.2.16 on 2022-10-24 19:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0015_auto_20210303_2000"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="migrated_from_sg",
            field=models.BooleanField(default=False),
        ),
    ]