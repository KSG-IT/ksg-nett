# Generated by Django 3.2.16 on 2022-12-14 16:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0002_initial"),
        ("users", "0002_auto_20221214_1506"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="admission",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="admissions.admission",
            ),
        ),
    ]
