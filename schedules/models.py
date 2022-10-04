import pytz
import datetime
from django.db import models
from model_utils.models import TimeFramedModel
from django.utils.translation import ugettext_lazy as _
from organization.models import InternalGroup, InternalGroupPosition
from users.models import User
from django.utils import timezone

from django.conf import settings


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

    def shifts_from_range(self, shifts_from, number_of_weeks):
        monday = shifts_from - timezone.timedelta(days=shifts_from.weekday())
        monday = timezone.datetime.combine(
            monday, datetime.time(), tzinfo=pytz.timezone(settings.TIME_ZONE)
        )
        sunday = monday + timezone.timedelta(days=6)
        sunday = sunday + timezone.timedelta(days=7) * number_of_weeks
        shifts = Shift.objects.filter(
            schedule=self, datetime_start__gte=monday, datetime_end__lte=sunday
        ).order_by("datetime_start")

        return shifts

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Schedule(name={self.name})"


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
        STROSSA = "STROSSA", _("Strossa")
        DAGLIGHALLEN_BAR = "DAGLIGHALLEN_BAR", _("Daglighallen Bar")

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

    def __str__(self):
        return f"{self.datetime_start.strftime('%Y-%-m-%-d')} {self.schedule.name}: {self.name}"


class ShiftSlot(models.Model):
    class Meta:
        verbose_name_plural = "Shift slots"

    class RoleOption(models.TextChoices):
        BARISTA = ("BARISTA", "Barista")
        KAFEANSVARLIG = ("KAFEANSVARLIG", "Kaféansvarlig")
        BARSERVITOR = ("BARSERVITOR", "Barservitør")
        HOVMESTER = ("HOVMESTER", "Hovmester")
        KOKK = ("KOKK", "Kokk")
        SOUSCHEF = ("SOUSCHEF", "Souschef")
        ARRANGEMENTBARTENDER = ("ARRANGEMENTBARTENDER", "Arrangementbartender")
        ARRANGAMENTANSVARLIG = ("ARRANGEMENTANSVARLIG", "Arrangementansvarlig")
        BRYGGER = ("BRYGGER", "Brygger")
        BARTENDER = ("BARTENDER", "Bartender")
        BARSJEF = ("BARSJEF", "Barsjef")
        SPRITBARTENDER = ("SPRITBARTENDER", "Spritbartender")
        SPRITBARSJEF = ("SPRITBARSJEF", "Spritbarsjef")

        UGLE = ("UGLE", "Ugle")
        BRANNVAKT = ("BRANNVAKT", "Brannvakt")
        RYDDEVAKT = ("RYDDEVAKT", "Ryddevakt")
        SOCIVAKT = ("SOCIVAKT", "Socivakt")

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
        max_length=64, choices=ShiftSlot.RoleOption.choices, null=False, blank=False
    )
    count = models.IntegerField()

    def __str__(self):
        return "Template for ShiftSlot %s for shift-template %s" % (
            self.role,
            self.shift_template.name,
        )
