# Generated by Django 4.2.3 on 2023-08-19 12:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0003_auto_20230110_1123"),
        ("admissions", "0010_applicantrecommendation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="admissionavailableinternalgrouppositiondata",
            name="internal_group_position",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="admission_data_instances",
                to="organization.internalgroupposition",
            ),
        ),
    ]