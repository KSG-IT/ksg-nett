# Generated by Django 3.2.13 on 2022-06-20 14:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0027_internalgroup_group_icon"),
        (
            "admissions",
            "0041_alter_internalgrouppositionpriority_internal_group_priority",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="ApplicantInterest",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "applicant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="internal_group_interests",
                        to="admissions.applicant",
                    ),
                ),
                (
                    "internal_group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="applicant_interests",
                        to="organization.internalgroup",
                    ),
                ),
            ],
            options={
                "verbose_name": "Applicant interest",
                "verbose_name_plural": "Applicant interests",
            },
        ),
    ]
