# Generated by Django 4.2.7 on 2025-03-17 09:31

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_alter_knighthood_knighted_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="knighthood",
            name="knighted_at",
            field=models.DateField(default=datetime.date(2025, 3, 17)),
        ),
    ]
