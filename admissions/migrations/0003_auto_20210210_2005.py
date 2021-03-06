# Generated by Django 3.1.6 on 2021-02-10 20:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0002_auto_20210207_1314"),
    ]

    operations = [
        migrations.AlterField(
            model_name="applicant",
            name="admissions",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="applicants",
                to="admissions.admission",
            ),
        ),
    ]
