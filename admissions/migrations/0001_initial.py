# Generated by Django 3.2.16 on 2022-12-04 20:24

import datetime
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Admission",
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
                    "date",
                    models.DateField(
                        blank=True, default=django.utils.timezone.now, null=True
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("configuration", "Configuration"),
                            ("open", "Open"),
                            ("in-session", "In session"),
                            ("locked", "Locked"),
                            ("closed", "Closed"),
                        ],
                        default="open",
                        max_length=32,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AdmissionAvailableInternalGroupPositionData",
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
                    "membership_type",
                    models.CharField(
                        choices=[
                            ("functionary", "Functionary"),
                            ("active-functionary-pang", "Active functionary pang"),
                            ("old-functionary-pang", "Old functionary pang"),
                            ("gang-member", "Gang member"),
                            ("active-gang-member-pang", "Active gang member pang"),
                            ("old-gang-member-pang", "Old gang member pang"),
                            ("interest-group-member", "Interest group member"),
                            ("hangaround", "Hangaround"),
                            ("temporary-leave", "Temporary leave"),
                        ],
                        default="gang-member",
                        max_length=32,
                    ),
                ),
                ("available_positions", models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name="Applicant",
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
                ("first_name", models.CharField(max_length=100, null=True)),
                ("last_name", models.CharField(max_length=100, null=True)),
                (
                    "phone",
                    models.CharField(blank=True, default="", max_length=12, null=True),
                ),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("date_of_birth", models.DateField(blank=True, null=True)),
                ("study", models.CharField(blank=True, default="", max_length=18)),
                ("address", models.CharField(blank=True, default="", max_length=30)),
                ("hometown", models.CharField(blank=True, default="", max_length=30)),
                ("wants_digital_interview", models.BooleanField(default=False)),
                ("will_be_admitted", models.BooleanField(default=False)),
                ("can_commit_three_semesters", models.BooleanField(default=True)),
                (
                    "cannot_commit_three_semesters_details",
                    models.CharField(blank=True, max_length=128, null=True),
                ),
                ("open_for_other_positions", models.BooleanField(default=False)),
                ("gdpr_consent", models.BooleanField(default=False)),
                ("last_activity", models.DateTimeField(blank=True, null=True)),
                ("last_notice", models.DateTimeField(blank=True, null=True)),
                (
                    "notice_method",
                    models.CharField(
                        blank=True,
                        choices=[("email", "Email"), ("call", "Call")],
                        default=None,
                        max_length=32,
                        null=True,
                    ),
                ),
                ("notice_comment", models.TextField(blank=True, default="")),
                ("token", models.CharField(max_length=64, null=True)),
                (
                    "image",
                    models.ImageField(blank=True, null=True, upload_to="applicants"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("email-sent", "Email sent"),
                            ("has-registered-profile", "Has registered profile"),
                            ("has-set-priorities", "Has set priorities"),
                            ("scheduled-interview", "Scheduled interview"),
                            ("interview-finished", "Interview finished"),
                            (
                                "did-not-show-up-for-interview",
                                "Did not show up for interview",
                            ),
                            ("retracted-application", "Retracted application"),
                        ],
                        default="email-sent",
                        max_length=64,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ApplicantComment",
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("text", models.TextField()),
            ],
            options={
                "verbose_name": "Applicant comment",
                "verbose_name_plural": "Applicant comments",
            },
        ),
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
            ],
            options={
                "verbose_name": "Applicant interest",
                "verbose_name_plural": "Applicant interests",
            },
        ),
        migrations.CreateModel(
            name="ApplicantUnavailability",
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
                ("datetime_start", models.DateTimeField()),
                ("datetime_end", models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name="InternalGroupPositionPriority",
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
                            ("probably-want", "Probably want"),
                            ("do-not-want", "Do not want"),
                            ("reserve", "Reserve"),
                            ("currently-discussing", "Currently discussing"),
                            ("pass-around", "Pass around"),
                            ("interested", "Interested"),
                        ],
                        max_length=24,
                        null=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "Internal group position priority",
                "verbose_name_plural": "Internal group position priorities",
            },
        ),
        migrations.CreateModel(
            name="Interview",
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
                ("interview_start", models.DateTimeField()),
                ("interview_end", models.DateTimeField()),
                ("notes", models.TextField(blank=True, default="")),
                ("discussion", models.TextField(blank=True, default="")),
                (
                    "total_evaluation",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("very-poor", "Very poor"),
                            ("poor", "Poor"),
                            ("medium", "Medium"),
                            ("good", "Good"),
                            ("very-good", "Very good"),
                        ],
                        default=None,
                        max_length=32,
                        null=True,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="InterviewAdditionalEvaluationStatement",
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
                ("statement", models.CharField(max_length=64, unique=True)),
                ("order", models.IntegerField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="InterviewBooleanEvaluation",
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
                ("statement", models.CharField(max_length=64, unique=True)),
                ("order", models.IntegerField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="InterviewLocation",
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
                ("name", models.CharField(max_length=32, unique=True)),
                (
                    "location_description",
                    models.TextField(
                        help_text="Tells the applicant details about the location. For example where to meet up before the interview.",
                        null=True,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="InterviewScheduleTemplate",
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
                ("interview_period_start_date", models.DateField()),
                ("interview_period_end_date", models.DateField()),
                (
                    "default_interview_day_start",
                    models.TimeField(default=datetime.time(12, 0)),
                ),
                (
                    "default_interview_day_end",
                    models.TimeField(default=datetime.time(18, 0)),
                ),
                (
                    "default_interview_duration",
                    models.DurationField(default=datetime.timedelta(seconds=1800)),
                ),
                (
                    "default_block_size",
                    models.IntegerField(
                        default=5,
                        help_text="Number of interviews happening back to back before a break",
                    ),
                ),
                (
                    "default_pause_duration",
                    models.DurationField(default=datetime.timedelta(seconds=3600)),
                ),
            ],
        ),
        migrations.CreateModel(
            name="InterviewLocationAvailability",
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
                ("datetime_from", models.DateTimeField()),
                ("datetime_to", models.DateTimeField()),
                (
                    "interview_location",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="availability",
                        to="admissions.interviewlocation",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="InterviewBooleanEvaluationAnswer",
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
                ("value", models.BooleanField(blank=True, default=None, null=True)),
                (
                    "interview",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="boolean_evaluation_answers",
                        to="admissions.interview",
                    ),
                ),
                (
                    "statement",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="admissions.interviewbooleanevaluation",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="InterviewAdditionalEvaluationAnswer",
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
                    "answer",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("very-little", "Very little"),
                            ("little", "Little"),
                            ("medium", "Medium"),
                            ("somewhat", "Somewhat"),
                            ("very", "Very"),
                        ],
                        default=None,
                        max_length=32,
                        null=True,
                    ),
                ),
                (
                    "interview",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="additional_evaluation_answers",
                        to="admissions.interview",
                    ),
                ),
                (
                    "statement",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="admissions.interviewadditionalevaluationstatement",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="interview",
            name="additional_evaluations",
            field=models.ManyToManyField(
                through="admissions.InterviewAdditionalEvaluationAnswer",
                to="admissions.InterviewAdditionalEvaluationStatement",
            ),
        ),
        migrations.AddField(
            model_name="interview",
            name="boolean_evaluations",
            field=models.ManyToManyField(
                through="admissions.InterviewBooleanEvaluationAnswer",
                to="admissions.InterviewBooleanEvaluation",
            ),
        ),
    ]
