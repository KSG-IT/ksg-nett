# Generated by Django 3.1.6 on 2021-02-09 17:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0018_auto_20210204_2016"),
    ]

    operations = [
        migrations.AlterField(
            model_name="internalgroupposition",
            name="name",
            field=models.CharField(max_length=32),
        ),
    ]
