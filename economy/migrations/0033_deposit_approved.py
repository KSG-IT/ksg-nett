# Generated by Django 3.2.16 on 2022-11-15 23:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("economy", "0032_auto_20221116_0026"),
    ]

    operations = [
        migrations.AddField(
            model_name="deposit",
            name="approved",
            field=models.BooleanField(default=False),
        ),
    ]