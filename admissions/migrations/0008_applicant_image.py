# Generated by Django 3.2.5 on 2021-11-16 16:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0007_alter_internalgrouppriority_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="applicant",
            name="image",
            field=models.ImageField(null=True, upload_to="applicants"),
        ),
    ]
