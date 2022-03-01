from django.db import models
from django.db.models import Q
from common.util import get_semester_year_shorthand
from django.utils import timezone
from django.db.utils import IntegrityError
from django.core.validators import MinValueValidator
from admissions.consts import (
    Priority,
    ApplicantStatus,
    InternalGroupStatus,
    AdmissionStatus,
)
from django.utils.translation import ugettext_lazy as _
from secrets import token_urlsafe
from os.path import join as osjoin
from admissions.utils import send_welcome_to_interview_email
import datetime


class AdmissionAvailableInternalGroupPositionData(models.Model):
    """
    Manages additional data for each relationship between an internal group position and the
    admission process its available for.
    """

    class Meta:
        unique_together = ("admission", "internal_group_position")

    admission = models.ForeignKey(
        "admissions.Admission",
        on_delete=models.CASCADE,
        related_name="available_internal_group_positions_data",
    )
    internal_group_position = models.ForeignKey(
        "organization.InternalGroupPosition", on_delete=models.CASCADE
    )
    available_positions = models.IntegerField()


class Admission(models.Model):
    date = models.DateField(blank=True, null=True, default=timezone.now)
    status = models.CharField(
        choices=AdmissionStatus.choices, default=AdmissionStatus.OPEN, max_length=32
    )

    available_internal_group_positions = models.ManyToManyField(
        "organization.InternalGroupPosition",
        through=AdmissionAvailableInternalGroupPositionData,
    )

    @property
    def semester(self) -> str:
        return get_semester_year_shorthand(self.date)

    @property
    def number_of_applicants(self):
        return self.applicants.count()

    @classmethod
    def get_or_create_current_admission(cls):
        active_admission = cls.objects.filter(~Q(status=AdmissionStatus.CLOSED))
        if len(active_admission) > 1:
            raise cls.MultipleObjectsReturned

        if not active_admission:
            active_admission = cls.objects.create(date=timezone.datetime.now())

        return active_admission.first()

    @classmethod
    def get_active_admission(cls):
        return cls.objects.filter(~Q(status="closed")).first()

    def __str__(self):
        return f"Admission for {self.semester}"


class InterviewBooleanEvaluation(models.Model):
    """
    An interview question with a yes/no type evaluation. An example would be
    "Could the applicant be good for night shifts?"
    """

    statement = models.CharField(max_length=64, null=False, blank=False, unique=True)
    order = models.IntegerField(unique=True)

    def __str__(self):
        return self.statement


class InterviewBooleanEvaluationAnswer(models.Model):
    class Meta:
        unique_together = ("interview", "statement")

    interview = models.ForeignKey(
        "admissions.Interview",
        on_delete=models.CASCADE,
        related_name="boolean_evaluation_answers",
    )
    statement = models.ForeignKey(
        "admissions.InterviewBooleanEvaluation", on_delete=models.CASCADE
    )
    value = models.BooleanField(null=False, blank=False)


class InterviewAdditionalEvaluationStatement(models.Model):
    """
    An interview question with a range of values stating how true this statment is for this person.
    An example would be "Is this person energetic?"
    """

    statement = models.CharField(max_length=64, unique=True)
    order = models.IntegerField(unique=True)

    def __str__(self):
        return self.statement


class InterviewAdditionalEvaluationAnswer(models.Model):
    class Meta:
        unique_together = ("interview", "statement")

    class Options(models.TextChoices):
        VERY_LITTLE = ("very-little", _("Very little"))
        LITTLE = (
            "little",
            _(
                "Little",
            ),
        )
        MEDIUM = (
            "medium",
            _(
                "Medium",
            ),
        )
        SOMEWHAT = ("somewhat", _("Somewhat"))
        VERY = ("very", _("Very"))

    interview = models.ForeignKey(
        "admissions.Interview",
        on_delete=models.CASCADE,
        related_name="additional_evaluation_statement_answers",
    )
    statement = models.ForeignKey(
        "admissions.InterviewAdditionalEvaluationStatement", on_delete=models.CASCADE
    )
    answer = models.CharField(
        max_length=32, choices=Options.choices, null=False, blank=False
    )

    def __str__(self):
        return self.answer


class Interview(models.Model):
    """
    An interview is a combination of a
    """

    class Meta:
        unique_together = ("interview_start", "interview_end", "location")

    class EvaluationOptions(models.TextChoices):
        VERY_POOR = ("very-poor", _("Very poor"))
        POOR = ("poor", _("Poor"))
        MEDIUM = (
            "medium",
            _("Medium"),
        )
        GOOD = ("good", _("Good"))
        VERY_GOOD = ("very-good", _("Very good"))

    interview_start = models.DateTimeField(null=False)
    interview_end = models.DateTimeField(null=False)
    notes = models.TextField(blank=True, default="")
    discussion = models.TextField(blank=True, default="")
    interviewers = models.ManyToManyField(
        "users.User", related_name="interviews_attended"
    )
    total_evaluation = models.CharField(
        max_length=32, choices=EvaluationOptions.choices, default=None, null=True
    )
    can_commit_three_semesters = models.BooleanField(default=True)
    cannot_commit_three_semesters_details = models.CharField(
        max_length=128, null=True, blank=True
    )

    boolean_evaluations = models.ManyToManyField(
        InterviewBooleanEvaluation, through=InterviewBooleanEvaluationAnswer
    )

    additional_evaluations = models.ManyToManyField(
        InterviewAdditionalEvaluationStatement,
        through=InterviewAdditionalEvaluationAnswer,
    )
    location = models.ForeignKey(
        "admissions.InterviewLocation", on_delete=models.CASCADE
    )

    def save(self, *args, **kwargs):
        """
        An interview cannot overlap in the same location. Whe therefore make the following checks
        """
        try:
            Interview.objects.get(
                # First we check if we are trying to start an interview during another one
                (
                    Q(interview_end__gt=self.interview_start)
                    & Q(interview_start__lt=self.interview_start)
                )
                | (  # Then we check if the end of the interview is during another one
                    Q(interview_start__lt=self.interview_end)
                    & Q(interview_end__gt=self.interview_end)
                ),
                location=self.location,
            )
        except self.DoesNotExist:
            super(Interview, self).save(*args, **kwargs)

    def __str__(self):
        return f"Interview slot at {self.location.name} from {self.interview_start} to {self.interview_end}"


class Applicant(models.Model):
    admission = models.ForeignKey(
        Admission, on_delete=models.CASCADE, related_name="applicants"
    )
    first_name = models.CharField(null=True, max_length=100)
    last_name = models.CharField(null=True, max_length=100)

    phone = models.CharField(default="", null=True, blank=True, max_length=12)
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(blank=True, null=True)

    study = models.CharField(default="", blank=True, max_length=18)
    address = models.CharField(default="", blank=True, max_length=30)
    hometown = models.CharField(default="", blank=True, max_length=30)

    wants_digital_interview = models.BooleanField(default=False)

    def image_dir(self, filename):
        # We want to save all objects in under the admission
        return osjoin("applicants", str(self.admission.semester), filename)

    # Use this for auth so they can access their application
    token = models.CharField(max_length=64, null=True)
    image = models.ImageField(upload_to=image_dir, null=True, blank=True)

    status = models.CharField(
        choices=ApplicantStatus.choices,
        max_length=64,
        default=ApplicantStatus.EMAIL_SENT,
    )

    interview = models.OneToOneField(
        Interview,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="applicant",
    )

    @classmethod
    def create_or_update_application(cls, email):
        """Can extend this method in the future to handle adding applications to new positions"""
        # We can consider changing this to send the email with bcc and then the link kan be requested
        current_admission = Admission.get_or_create_current_admission()
        auth_token = token_urlsafe(32)
        cls.objects.create(email=email, admission=current_admission, token=auth_token)

    @property
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"Applicant {self.get_full_name}"


class InternalGroupPositionPriority(models.Model):
    class Meta:
        verbose_name = "Internal group position priority"
        verbose_name_plural = "Internal group position priorities"
        unique_together = ("applicant", "applicant_priority")

    applicant = models.ForeignKey(
        Applicant, on_delete=models.CASCADE, related_name="priorities"
    )
    internal_group_position = models.ForeignKey(
        "organization.InternalGroupPosition",
        on_delete=models.CASCADE,
        related_name="applicant_priorities",
    )

    # Tells us how the applicant prioritizes internal groups in their application
    # This should maybe have more options than three?
    applicant_priority = models.CharField(choices=Priority.choices, max_length=12)

    # Tells us how an internal group prioritizes an applicant, null means not considered yet
    internal_group_priority = models.CharField(
        choices=InternalGroupStatus.choices,
        max_length=24,
        blank=True,
        null=True,
        default="",
    )

    def __str__(self):
        return (
            f"Admission {self.applicant.admission.semester} "
            f"{self.internal_group_position.name} {self.applicant_priority} choice for {self.applicant.get_full_name}"
        )


class ApplicantUnavailability(models.Model):
    # Periods of time the applicant is unavailable for calls
    applicant = models.ForeignKey(
        Applicant, on_delete=models.CASCADE, related_name="unavailability"
    )
    datetime_start = models.DateTimeField(null=False)
    datetime_end = models.DateTimeField(null=False)

    def __str__(self):
        return f"Applicant {self.applicant.get_full_name} unavailable from {self.datetime_start} to {self.datetime_end}"


class InterviewScheduleTemplate(models.Model):
    """Default template for generating interviews"""

    interview_period_start_date = models.DateField(null=False)
    interview_period_end_date = models.DateField(null=False)

    # The time of the first interview for each day in the interview period
    default_interview_day_start = models.TimeField(
        default=datetime.time(hour=12, minute=0)
    )
    # The time for the last interview for each day in the interview period
    default_interview_day_end = models.TimeField(
        default=datetime.time(hour=18, minute=0)
    )
    default_interview_duration = models.DurationField(
        default=timezone.timedelta(minutes=30)
    )

    # How many interviews exist before a longer break
    default_block_size = models.IntegerField(
        default=5,
        help_text="Number of interviews happening back to back before a break",
    )
    default_pause_duration = models.DurationField(default=timezone.timedelta(hours=1))

    def __str__(self):
        return f"Interview schedule template. Generates {self.default_block_size * 2} interviews per location per day"

    @classmethod
    def get_interview_schedule_template(cls):
        return cls.objects.all().first()

    @classmethod
    def get_or_create_interview_schedule_template(cls):
        schedule = cls.objects.all().first()
        if not schedule:
            schedule = cls()

        return schedule

    def save(self, *args, **kwargs):
        """
        An interview cannot overlap in the same location. Whe therefore make the following checks
        """
        if InterviewScheduleTemplate.objects.all().count() > 0 and self._state.adding:
            raise IntegrityError(
                "Only one InterviewScheduleTemplate can exist at a time"
            )
        super(InterviewScheduleTemplate, self).save(*args, **kwargs)


class InterviewLocation(models.Model):
    """Represents a location where an interview is held. The name can be a physical location or just 'Digital room 1"""

    name = models.CharField(max_length=32, unique=True)
    location_description = models.TextField(
        null=True,
        help_text="Tells the applicant details about the location. For example where to meet up before the interview.",
    )

    def __str__(self):
        return self.name


class InterviewLocationAvailability(models.Model):
    """Defines when a location is available to us. A location can have multiple intervals where its available to us"""

    # Should rename to just location. This is redundant
    interview_location = models.ForeignKey(
        InterviewLocation, related_name="availability", on_delete=models.CASCADE
    )
    datetime_from = models.DateTimeField()
    datetime_to = models.DateTimeField()

    def __str__(self):
        return f"{self.interview_location.name} available from {self.datetime_from} to {self.datetime_to}"
