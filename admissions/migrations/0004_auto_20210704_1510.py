# Generated by Django 3.2.3 on 2021-07-04 15:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0003_auto_20210210_2005"),
    ]

    operations = [
        migrations.RenameField(
            model_name="applicant",
            old_name="admissions",
            new_name="admission",
        ),
        migrations.AlterField(
            model_name="applicant",
            name="home_address",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.AlterField(
            model_name="applicant",
            name="phone",
            field=models.CharField(blank=True, default="", max_length=12, null=True),
        ),
        migrations.AlterField(
            model_name="applicant",
            name="study",
            field=models.CharField(blank=True, default="", max_length=18),
        ),
        migrations.AlterField(
            model_name="applicant",
            name="town_address",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
    ]