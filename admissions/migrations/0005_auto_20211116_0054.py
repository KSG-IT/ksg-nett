# Generated by Django 3.2.5 on 2021-11-16 00:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0022_auto_20210303_1939"),
        ("admissions", "0004_auto_20210704_1510"),
    ]

    operations = [
        migrations.AddField(
            model_name="applicant",
            name="status",
            field=models.CharField(
                choices=[("active", "Active"), ("retracted", "Retracted")],
                default="active",
                max_length=12,
            ),
        ),
        migrations.CreateModel(
            name="InternalGroupPriority",
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
                    "applicant_priority",
                    models.CharField(
                        choices=[
                            ("first", "First"),
                            ("second", "Second"),
                            ("third", "Third"),
                        ],
                        max_length=12,
                    ),
                ),
                (
                    "internal_group_priority",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("want", "Want"),
                            ("do-not-want", "Do not want"),
                            ("reserve", "Reserve"),
                            ("should-be-admitted", "Should be admitted"),
                        ],
                        default="",
                        max_length=24,
                        null=True,
                    ),
                ),
                (
                    "applicant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="priorities",
                        to="admissions.applicant",
                    ),
                ),
                (
                    "internal_group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="application_priorities",
                        to="organization.internalgroup",
                    ),
                ),
            ],
            options={
                "verbose_name": "Internal group priority",
                "verbose_name_plural": "Intern group priorities",
                "unique_together": {("applicant", "applicant_priority")},
            },
        ),
    ]