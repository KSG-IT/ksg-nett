import graphene
from django.db import models, transaction
from django.db.models import Q
from common.util import get_semester_year_shorthand
from django.utils import timezone
from django.db.utils import IntegrityError
from admissions.consts import (
    Priority,
    ApplicantStatus,
    InternalGroupStatus,
    AdmissionStatus,
)
from django.utils.translation import ugettext_lazy as _
from secrets import token_urlsafe
from os.path import join as osjoin

from organization.consts import InternalGroupPositionMembershipType
from organization.models import InternalGroup, InternalGroupPositionMembership
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
    membership_type = models.CharField(
        max_length=32,
        choices=InternalGroupPositionMembershipType.choices,
        default=InternalGroupPositionMembershipType.GANG_MEMBER,
        null=False,
        blank=False,
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

    def internal_groups_accepting_applicants(self):
        positions = self.available_internal_group_positions.all()
        internal_groups = InternalGroup.objects.filter(positions__in=positions)
        return internal_groups.order_by("name")

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
    # Nullable because we prepare this before the interview is booked
    value = models.BooleanField(default=None, null=True, blank=True)


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
        LITTLE = ("little", _("Little"))
        MEDIUM = ("medium", _("Medium"))
        SOMEWHAT = ("somewhat", _("Somewhat"))
        VERY = ("very", _("Very"))

    interview = models.ForeignKey(
        "admissions.Interview",
        on_delete=models.CASCADE,
        related_name="additional_evaluation_answers",
    )
    statement = models.ForeignKey(
        "admissions.InterviewAdditionalEvaluationStatement", on_delete=models.CASCADE
    )
    # Nullable because we prepare this before the interview is booked
    answer = models.CharField(
        default=None, max_length=32, choices=Options.choices, null=True, blank=True
    )


class Interview(models.Model):
    class Meta:
        unique_together = ("interview_start", "interview_end", "location")

    class EvaluationOptions(models.TextChoices):
        VERY_POOR = ("very-poor", _("Very poor"))
        POOR = ("poor", _("Poor"))
        MEDIUM = ("medium", _("Medium"))
        GOOD = ("good", _("Good"))
        VERY_GOOD = ("very-good", _("Very good"))

    interview_start = models.DateTimeField(null=False)
    interview_end = models.DateTimeField(null=False)
    notes = models.TextField(blank=True, default="")
    discussion = models.TextField(blank=True, default="")
    interviewers = models.ManyToManyField(
        "users.User", related_name="interviews_attended", blank=True
    )
    total_evaluation = models.CharField(
        max_length=32,
        choices=EvaluationOptions.choices,
        default=None,
        null=True,
        blank=True,
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

    @property
    def get_applicant(self):
        # https://stackoverflow.com/a/27042585
        if hasattr(self, "applicant"):
            return self.applicant
        return None

    def save(self, *args, **kwargs):
        """
        An interview cannot overlap in the same location. We therefore make the following checks
        """

        try:
            # In case we hit create button twice by accident from frontend
            Interview.objects.get(
                interview_start=self.interview_start,
                interview_end=self.interview_end,
                location=self.location,
            )
        except self.DoesNotExist:
            pass

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
    class NoticeMethod(models.TextChoices):
        EMAIL = ("email", _("Email"))
        CALL = ("call", _("Call"))

    admission = models.ForeignKey(
        Admission, on_delete=models.CASCADE, related_name="applicants"
    )
    first_name = models.CharField(null=True, max_length=100)
    last_name = models.CharField(null=True, max_length=100)

    phone = models.CharField(default="", null=True, blank=True, max_length=32)
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(blank=True, null=True)

    study = models.CharField(default="", blank=True, max_length=100)
    address = models.CharField(default="", blank=True, max_length=100)
    hometown = models.CharField(default="", blank=True, max_length=100)

    wants_digital_interview = models.BooleanField(default=False)
    will_be_admitted = models.BooleanField(default=False)

    can_commit_three_semesters = models.BooleanField(default=True)
    cannot_commit_three_semesters_details = models.CharField(
        max_length=128, null=True, blank=True
    )
    open_for_other_positions = models.BooleanField(default=False)
    gdpr_consent = models.BooleanField(default=False)

    # Used to track if the applicant has been given notice that they
    # have called in to an interview or not
    last_activity = models.DateTimeField(null=True, blank=True)
    last_notice = models.DateTimeField(null=True, blank=True)
    notice_method = models.CharField(
        default=None, choices=NoticeMethod.choices, max_length=32, null=True, blank=True
    )
    notice_comment = models.TextField(default="", null=False, blank=True)
    notice_user = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True
    )

    def image_dir(self, filename):
        # ToDo delete this with migration squash
        return osjoin("applicants", str(self.admission.semester), filename)

    # Use this for auth so they can access their application
    token = models.CharField(max_length=64, null=True)
    image = models.ImageField(upload_to="applicants", null=True, blank=True)

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
        current_admission = Admission.get_or_create_current_admission()
        auth_token = token_urlsafe(32)
        return cls.objects.create(
            email=email, admission=current_admission, token=auth_token
        )

    @classmethod
    def valid_applicants(cls):
        return Applicant.objects.filter(
            ~Q(priorities__internal_group_priority=InternalGroupStatus.DO_NOT_WANT),
            status=ApplicantStatus.INTERVIEW_FINISHED,
        )

    def add_priority(self, position):
        # In case a priority has been deleted we need to reorder existing ones first
        priorities = [Priority.FIRST, Priority.SECOND, Priority.THIRD]
        # Unfiltered priorities can have None values
        index = self.priorities.count()
        if index >= 3:
            raise IntegrityError("Applicant already has three priorities")

        priority = priorities[index]
        self.priorities.add(
            InternalGroupPositionPriority.objects.create(
                applicant=self,
                internal_group_position=position,
                applicant_priority=priority,
            )
        )

        self.save()

    def update_priority_order(self, new_priority_order):
        """
        We assume we receive a list of internal group positions in the desired order. We create a single
        transaction where were delete and then re-create the priority order.
        """
        priorities = [Priority.FIRST, Priority.SECOND, Priority.THIRD]
        with transaction.atomic():
            self.priorities.all().delete()

            for index, position in enumerate(new_priority_order):
                InternalGroupPositionPriority.objects.create(
                    applicant=self,
                    internal_group_position=position,
                    applicant_priority=priorities[index],
                )

    @property
    def get_priorities(self):
        # get_ pre-pending to avoid name conflicts
        first_priority = self.priorities.filter(
            applicant_priority=Priority.FIRST
        ).first()
        second_priority = self.priorities.filter(
            applicant_priority=Priority.SECOND
        ).first()
        third_priority = self.priorities.filter(
            applicant_priority=Priority.THIRD
        ).first()
        return [first_priority, second_priority, third_priority]

    @property
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        if not self.first_name:
            return "Unregistered applicant"
        return f"Applicant {self.get_full_name}"


class ApplicantInterest(models.Model):
    """
    A way to track when an internal group is interested in an applicant that has not
    explicitly applied to said internal group
    """

    class Meta:
        verbose_name = "Applicant interest"
        verbose_name_plural = "Applicant interests"

    class Type(models.TextChoices):
        # Currently not in use
        WANT = ("want", "Want")
        NEED = ("need", "Need")

    applicant = models.ForeignKey(
        Applicant, on_delete=models.CASCADE, related_name="internal_group_interests"
    )
    internal_group = models.ForeignKey(
        InternalGroup, on_delete=models.CASCADE, related_name="applicant_interests"
    )
    position_to_be_offered = models.ForeignKey(
        "organization.InternalGroupPosition",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="applicant_interest_offers",
    )

    def __str__(self):
        return f"{self.internal_group.name} interest in {self.applicant}"


class ApplicantComment(models.Model):
    class Meta:
        verbose_name = "Applicant comment"
        verbose_name_plural = "Applicant comments"

    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="applicant_comments"
    )
    applicant = models.ForeignKey(
        Applicant, on_delete=models.CASCADE, related_name="comments"
    )
    text = models.TextField()

    def __str__(self):
        return f"{self.user} comment on {self.applicant}"


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
    applicant_priority = models.CharField(choices=Priority.choices, max_length=12)

    # Tells us how an internal group prioritizes an applicant, null means not considered yet
    internal_group_priority = models.CharField(
        choices=InternalGroupStatus.choices,
        max_length=24,
        blank=True,
        null=True,
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
