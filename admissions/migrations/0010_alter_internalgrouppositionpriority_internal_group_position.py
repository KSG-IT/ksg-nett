# Generated by Django 3.2.11 on 2022-02-03 23:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0023_auto_20220130_2056"),
        ("admissions", "0009_auto_20220203_2306"),
    ]

    operations = [
        migrations.AlterField(
            model_name="internalgrouppositionpriority",
            name="internal_group_position",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="applicant_priorities",
                to="organization.internalgroupposition",
            ),
        ),
    ]