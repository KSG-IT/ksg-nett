from zoneinfo import ZoneInfo
from django.db import models
from django.utils.translation import gettext_lazy as _

from organization.consts import InternalGroupPositionMembershipType
from organization.models import (
    InternalGroup,
    InternalGroupPosition,
    InternalGroupPositionMembership,
)
from users.models import User
from django.utils import timezone
from django.conf import settings


class RoleOption(models.TextChoices):
    BARISTA = ("BARISTA", "Barista")
    KAFEANSVARLIG = ("KAFEANSVARLIG", "Kaféansvarlig")
    BARSERVITOR = ("BARSERVITOR", "Barservitør")
    HOVMESTER = ("HOVMESTER", "Hovmester")
    KOKK = ("KOKK", "Kokk")
    SOUSCHEF = ("SOUSCHEF", "Souschef")
    ARRANGEMENTBARTENDER = ("ARRANGEMENTBARTENDER", "Arrangementbartender")
    ARRANGEMENTANSVARLIG = ("ARRANGEMENTANSVARLIG", "Arrangementansvarlig")
    BRYGGER = ("BRYGGER", "Brygger")
    BARTENDER = ("BARTENDER", "Bartender")
    BARSJEF = ("BARSJEF", "Barsjef")
    SPRITBARTENDER = ("SPRITBARTENDER", "Spritbartender")
    SPRITBARSJEF = ("SPRITBARSJEF", "Spritbarsjef")
    UGLE = ("UGLE", "Ugle")
    BRANNVAKT = ("BRANNVAKT", "Brannvakt")
    RYDDEVAKT = ("RYDDEVAKT", "Ryddevakt")
    BAEREVAKT = ("BAEREVAKT", "Bærevakt")
    SOCIVAKT = ("SOCIVAKT", "Socivakt")


class Schedule(models.Model):
    """
    A schedule is a logical grouping of shifts. They are usually grouped together
    by internal group like 'Bargjengen' or 'Edgar' and 'Brannvakt'.
    """

    class Meta:
        verbose_name_plural = "schedules"

    class DisplayModeOptions(models.TextChoices):
        SINGLE_LOCATION = "SINGLE_LOCATION", _("Single location")
        MULTIPLE_LOCATIONS = "MULTIPLE_LOCATIONS", _("Multiple locations")

    name = models.CharField(max_length=100, unique=True)
    display_mode = models.CharField(
        max_length=20,
        choices=DisplayModeOptions.choices,
        default=DisplayModeOptions.SINGLE_LOCATION,
    )
    default_role = models.CharField(
        max_length=64, choices=RoleOption.choices, null=True, blank=False, default=None
    )
    # The internal group that staffs the schedule. Its functionaries with the
    # schedule permissions manage it. Without a group, anyone with the
    # permissions manages it. See schedules/permissions.py.
    internal_group = models.ForeignKey(
        InternalGroup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="schedules",
    )
    # Autofill gives a user at most this many shifts in a calendar week
    max_shifts_per_week = models.PositiveSmallIntegerField(default=2)

    def shifts_from_range(self, shifts_from, number_of_weeks):
        monday = shifts_from - timezone.timedelta(days=shifts_from.weekday())
        monday = timezone.datetime(
            year=monday.year,
            month=monday.month,
            day=monday.day,
        )
        monday = timezone.make_aware(monday, timezone=ZoneInfo(settings.TIME_ZONE))
        sunday = (
            monday
            + timezone.timedelta(days=6, hours=23, minutes=59, seconds=59)
            * number_of_weeks
        )

        shifts = Shift.objects.filter(
            schedule=self, datetime_start__gte=monday, datetime_start__lte=sunday
        ).order_by("datetime_start")

        return shifts

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Schedule(name={self.name})"

    @classmethod
    def get_all_current_shifts(cls):
        now = timezone.now()
        return Shift.objects.filter(datetime_start__lte=now, datetime_end__gte=now)

    @classmethod
    def get_all_users_working_now(cls):
        now = timezone.now()
        users = User.objects.filter(
            filled_shifts__shift__datetime_start__lte=now,
            filled_shifts__shift__datetime_end__gte=now,
        ).distinct()
        return users


class Shift(models.Model):
    class Meta:
        verbose_name_plural = "shifts"

    class Location(models.TextChoices):
        EDGAR = "EDGAR", _("Edgar")
        BODEGAEN = "BODEGAEN", _("Bodegaen")
        RUNDHALLEN = "RUNDHALLEN", _("Rundhallen")
        KLUBBEN = "KLUBBEN", _("Klubben")
        LYCHE_BAR = "LYCHE_BAR", _("Lyche Bar")
        LYCHE_KJOKKEN = "LYCHE_KJOKKEN", _("Lyche Kjøkken")
        STORSALEN = "STORSALEN", _("Storsalen")
        SELSKAPSSIDEN = "SELSKAPSSIDEN", _("Selskapssiden")
        SERVERING_C = "SERVERING_C", _("Servering C")
        SERVERING_D = "SERVERING_D", _("Servering D")
        SERVERING_K = "SERVERING_K", _("Servering K")
        STROSSA = "STROSSA", _("Strossa")
        DAGLIGHALLEN_BAR = "DAGLIGHALLEN_BAR", _("Daglighallen Bar")
        KONTORET = "KONTORET", _("Kontoret")

    name = models.CharField(max_length=69, null=False, blank=False)
    location = models.CharField(
        max_length=64, choices=Location.choices, blank=True, null=True
    )
    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="shifts",
    )
    datetime_start = models.DateTimeField(null=False, blank=False)
    datetime_end = models.DateTimeField(null=False, blank=False)
    generated_from = models.ForeignKey(
        "schedules.ScheduleTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shifts_generated",
    )
    internal_control_document = models.ForeignKey(
        "internalcontrol.InternalControlDocument",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shifts",
    )

    @property
    def is_filled(self):
        empty_slots = self.slots.filter(user__isnull=True)
        return not empty_slots.exists()

    def __str__(self):
        return f"{self.datetime_start.strftime('%Y-%-m-%-d')} {self.schedule.name}: {self.name}"

    def save(self, *args, **kwargs):
        if self.datetime_start > self.datetime_end:
            raise ValueError("datetime_start must be before datetime_end")
        super().save(*args, **kwargs)


class ShiftSlot(models.Model):
    class Meta:
        verbose_name_plural = "Shift slots"

    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name="slots")
    user = models.ForeignKey(
        User,
        default=None,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="filled_shifts",
    )
    role = models.CharField(
        max_length=64, choices=RoleOption.choices, null=False, blank=False
    )


class ShiftTrade(models.Model):
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name="trades")
    verified_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    class TradeStatus(models.TextChoices):
        OFFERED = "OFFERED", _("Offered")
        REQUESTED = "REQUESTED", _("Requested")
        COMPLETE = "COMPLETE", _("Complete")

    status = models.CharField(
        choices=TradeStatus.choices, default=TradeStatus.OFFERED, max_length=32
    )
    offeror = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="shift_trades_offered"
    )
    taker = models.ForeignKey(
        User, null=True, on_delete=models.SET_NULL, related_name="shift_trades_taken"
    )


class ScheduleTemplate(models.Model):
    """
    Groups together a weeks worth of shifts that can be applied to an arbitrary week.
    Most internal groups will only have a ordinary week (standard uke) and 'immen'.
    """

    name = models.CharField(max_length=100)
    schedule = models.ForeignKey(
        Schedule, blank=False, null=False, on_delete=models.CASCADE
    )

    def __str__(self):
        return "Template %s for schedule %s" % (self.name, self.schedule.name)

    def __repr__(self):
        return "ScheduleTemplate(name=%s, schedule=%s)" % (
            self.name,
            self.schedule.name,
        )

    class Meta:
        verbose_name_plural = "schedule templates"
        unique_together = (
            (
                "name",
                "schedule",
            ),
        )


class ShiftTemplate(models.Model):
    """
    A shift template encapsulates a shift occurring in the context of a Week.
    If we have the schedule template 'Standard uke' that belongs to the internal
    group 'Bargjengen' A typical ShiftTemplate would be

    ShiftTemplate(
        name='Helgevakt',
        location='BODEGAEN',
        day='FRIDAY',
        time_start='20:00'
        time_end='03:00'
    )
    """

    class Day(models.TextChoices):
        MONDAY = "MONDAY", _("Monday")
        TUESDAY = "TUESDAY", _("Tuesday")
        WEDNESDAY = "WEDNESDAY", _("Wednesday")
        THURSDAY = "THURSDAY", _("Thursday")
        FRIDAY = "FRIDAY", _("Friday")
        SATURDAY = "SATURDAY", _("Saturday")
        SUNDAY = "SUNDAY", _("Sunday")

    name = models.CharField(
        max_length=100, help_text="Name that will be applied to the generated shift"
    )
    schedule_template = models.ForeignKey(
        ScheduleTemplate,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="shift_templates",
    )
    location = models.CharField(
        max_length=64, choices=Shift.Location.choices, null=True, blank=True
    )
    day = models.CharField(
        choices=Day.choices,
        max_length=32,
        help_text="Day of the week this shift occurs",
    )
    internal_control_document_template = models.ForeignKey(
        "internalcontrol.InternalControlDocumentTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shift_templates",
    )

    # time_end < time_start means that the shift is over midnight
    time_start = models.TimeField()
    time_end = models.TimeField()

    def __str__(self):
        return "Template for ShiftSlotGroup %s for schedule-template %s" % (
            self.name,
            self.schedule_template.name,
        )

    def __repr__(self):
        return "ShiftSlotGroupTemplate(name=%s, schedule_template=%s" % (
            self.name,
            self.schedule_template.name,
        )

    class Meta:
        verbose_name_plural = "Shift templates"


class ShiftSlotTemplate(models.Model):
    class Meta:
        verbose_name_plural = "Shift slot templates"
        unique_together = (
            (
                "shift_template",
                "role",
            ),
        )

    shift_template = models.ForeignKey(
        ShiftTemplate,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="shift_slot_templates",
    )
    role = models.CharField(
        max_length=64, choices=RoleOption.choices, null=False, blank=False
    )
    count = models.IntegerField()

    def __str__(self):
        return "Template for ShiftSlot %s for shift-template %s" % (
            self.role,
            self.shift_template.name,
        )


class ShiftInterest(models.Model):
    class InterestTypes(models.TextChoices):
        INTERESTED = "interested"
        AVAILABLE = "available"
        UNAVAILABLE = "unavailable"

    shift = models.ForeignKey(
        Shift,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="interests",
    )

    user = models.ForeignKey(
        User,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
    )

    class Source(models.TextChoices):
        MANUAL = "manual", _("Manual")
        # Pre-filled from the user's weekly unavailability
        UNAVAILABILITY = "unavailability", _("Unavailability")

    interest_type = models.CharField(
        default=InterestTypes.INTERESTED, choices=InterestTypes.choices, max_length=12
    )
    # A note to the schedule managers, for example why the user cannot work
    note = models.CharField(max_length=255, blank=True, default="")
    source = models.CharField(
        max_length=16, choices=Source.choices, default=Source.MANUAL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["shift", "user"], name="unique_shift_interest_user"
            )
        ]


class DefaultAvailability(models.TextChoices):
    # No answer for a shift means "can work"
    AVAILABLE = "available", _("Available")
    # No answer for a shift means "cannot work"
    OPT_IN = "opt_in", _("Opt in")


class ScheduleRosterGrouping(models.Model):
    """
    A rule for the roster sync: active members with this position and
    membership type are on the roster of the schedule, with these values.
    See schedules/utils/roster.py.
    """

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["schedule", "internal_group_position", "position_type"],
                name="unique_roster_grouping",
            )
        ]

    schedule = models.ForeignKey(
        Schedule, on_delete=models.CASCADE, related_name="roster_groupings"
    )
    internal_group_position = models.ForeignKey(
        InternalGroupPosition, on_delete=models.CASCADE, related_name="+"
    )
    position_type = models.CharField(
        max_length=32, choices=InternalGroupPositionMembershipType.choices
    )
    role = models.CharField(max_length=64, choices=RoleOption.choices)
    default_availability = models.CharField(
        max_length=12, choices=DefaultAvailability.choices
    )
    # The most shifts between two admissions. Null means no cap.
    shift_cap = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return (
            f"{self.schedule.name}: {self.internal_group_position.name} "
            f"{self.position_type} as {self.role}"
        )


class ScheduleRoster(models.Model):
    """
    One row per user on the roster of a schedule. The roster sync writes the
    rows from the groupings. A manager can edit a row or add one by hand.
    """

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["schedule", "user"], name="unique_schedule_roster_user"
            )
        ]

    schedule = models.ForeignKey(
        Schedule,
        blank=False,
        null=False,
        on_delete=models.CASCADE,
        related_name="roster",
    )

    user = models.ForeignKey(
        User, blank=False, null=False, on_delete=models.CASCADE, related_name="rosters"
    )

    autofill_as = models.CharField(
        max_length=64, choices=RoleOption.choices, null=False, blank=False
    )
    default_availability = models.CharField(
        max_length=12,
        choices=DefaultAvailability.choices,
        default=DefaultAvailability.AVAILABLE,
    )
    shift_cap = models.PositiveSmallIntegerField(null=True, blank=True)
    # The rule that added the row. Null for a row added by hand, or when the
    # rule was deleted.
    grouping = models.ForeignKey(
        ScheduleRosterGrouping,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="roster_entries",
    )
    # The sync does not change the values of an edited row
    manually_edited = models.BooleanField(default=False)
    # A manager added the row. The sync removes it only when the user leaves.
    added_manually = models.BooleanField(default=False)
    # Count shifts from this date when it is after the last admission closed
    count_from = models.DateField(null=True, blank=True)


class PlanningPeriod(models.Model):
    """
    The shifts of a schedule from date_from to date_to, both included. Users on
    the roster answer for the shifts until the deadline. Then the managers make
    and publish the plan.
    """

    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        CLOSED = "closed", _("Closed")
        PUBLISHED = "published", _("Published")

    class Meta:
        ordering = ["-date_from"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(date_to__gte=models.F("date_from")),
                name="planning_period_dates_in_order",
            )
        ]

    schedule = models.ForeignKey(
        Schedule, on_delete=models.CASCADE, related_name="planning_periods"
    )
    date_from = models.DateField()
    date_to = models.DateField()
    deadline = models.DateTimeField()
    published_at = models.DateTimeField(null=True, blank=True)
    # When a manager last sent the availability reminder
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.schedule.name}: {self.date_from} to {self.date_to}"

    @property
    def status(self):
        if self.published_at:
            return self.Status.PUBLISHED
        if timezone.now() < self.deadline:
            return self.Status.OPEN
        return self.Status.CLOSED

    def shifts(self):
        # __date uses settings.TIME_ZONE, so a shift belongs to its local date
        return Shift.objects.filter(
            schedule=self.schedule,
            datetime_start__date__gte=self.date_from,
            datetime_start__date__lte=self.date_to,
        ).order_by("datetime_start")

    @classmethod
    def overlapping(cls, schedule, date_from, date_to, exclude=None):
        periods = cls.objects.filter(
            schedule=schedule, date_from__lte=date_to, date_to__gte=date_from
        )
        if exclude is not None:
            periods = periods.exclude(pk=exclude.pk)
        return periods

    @classmethod
    def for_shift(cls, shift):
        day = timezone.localdate(shift.datetime_start)
        return cls.objects.filter(
            schedule_id=shift.schedule_id, date_from__lte=day, date_to__gte=day
        ).first()


class UserUnavailability(models.Model):
    """
    A time on a weekday when the user cannot work. It repeats each week, like a
    ShiftTemplate, and applies to all schedules. It pre-fills "cannot work" for
    the shifts it overlaps, see schedules/utils/unavailability.py.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="unavailabilities"
    )
    day = models.CharField(max_length=10, choices=ShiftTemplate.Day.choices)
    time_start = models.TimeField()
    # At or before time_start means the next day
    time_end = models.TimeField()
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user}: {self.day} {self.time_start}-{self.time_end}"


class ScheduleAutofillRun(models.Model):
    """
    One autofill of a planning period. Its result is ShiftSlotDraft rows with
    autofill_run set, and the slots it could not fill, with a reason.
    See schedules/utils/autofill.py.
    """

    class Meta:
        ordering = ["-created_at"]

    period = models.ForeignKey(
        PlanningPeriod, on_delete=models.CASCADE, related_name="autofill_runs"
    )
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    # [{"slot": slot id, "reason": UnfilledReason, "candidates": int}]
    unfilled = models.JSONField(default=list)


class ShiftSlotDraft(models.Model):
    """
    A change to a slot that is not visible to the members yet. A null user
    removes the person from the slot. lockDraft copies the drafts to the slots.
    See schedules/utils/drafts.py.
    """

    slot = models.OneToOneField(
        ShiftSlot, on_delete=models.CASCADE, related_name="draft"
    )
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    changed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    changed_at = models.DateTimeField(auto_now=True)
    # The autofill run that made the draft. Null for a manual draft; a new run
    # of autofill keeps manual drafts.
    autofill_run = models.ForeignKey(
        ScheduleAutofillRun,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="drafts",
    )

    def __str__(self):
        return f"Draft of {self.slot}: {self.user}"
