# Generated by Django 3.2.13 on 2022-09-13 15:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0029_auto_20220913_1711"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="schedulerole",
            options={"verbose_name_plural": "schedule roles"},
        ),
        migrations.AlterField(
            model_name="shift",
            name="name",
            field=models.CharField(max_length=69),
        ),
    ]
