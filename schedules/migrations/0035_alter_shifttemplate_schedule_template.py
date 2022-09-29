# Generated by Django 3.2.13 on 2022-09-28 18:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0034_shifttemplate_location"),
    ]

    operations = [
        migrations.AlterField(
            model_name="shifttemplate",
            name="schedule_template",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="shift_templates",
                to="schedules.scheduletemplate",
            ),
        ),
    ]
