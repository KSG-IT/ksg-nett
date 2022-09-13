from django.db import models
from model_utils.models import TimeFramedModel
from django.utils.translation import ugettext_lazy as _
from organization.models import InternalGroup, InternalGroupPosition
from users.models import User


class Schedule(models.Model):
    """
    A schedule is a logical grouping of shifts. They are usually grouped together
    by internal group like 'Bargjengen' or 'Edgar' and 'Brannvakt'.
    """

    class Meta:
        verbose_name_plural = "schedules"

    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Schedule(name={self.name})"


class ScheduleRole(models.Model):
    """
    Roles are unique to a schedule. Edgar has 'Barista' and 'Kaféansvarlig'
    whereas Uglevakt and Brannvakt only has 'ugle' and 'brannansvarlig'
    """

    class Meta:
        verbose_name_plural = "schedule roles"
        unique_together = ("schedule", "name")

    schedule = models.ForeignKey(
        Schedule, on_delete=models.CASCADE, related_name="roles"
    )
    name = models.CharField(max_length=100, null=False, blank=False)

    def __str__(self):
        return self.name


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
        Schedule, on_delete=models.CASCADE, null=False, blank=False
    )
    datetime_start = models.DateTimeField(null=False, blank=False)
    datetime_end = models.DateTimeField(null=False, blank=False)

    def __str__(self):
        return f"{self.schedule.name}: {self.name}"


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
    role = models.ForeignKey(
        ScheduleRole,
        null=False,
        blank=False,
        on_delete=models.DO_NOTHING,
        related_name="shift_slots",
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
    class Day(models.TextChoices):
        MONDAY = "MONDAY", _("Monday")
        TUESDAY = "TUESDAY", _("Tuesday")
        WEDNESDAY = "WEDNESDAY", _("Wednesday")
        THURSDAY = "THURSDAY", _("Thursday")
        FRIDAY = "FRIDAY", _("Friday")
        SATURDAY = "SATURDAY", _("Saturday")
        SUNDAY = "SUNDAY", _("Sunday")

    name = models.CharField(max_length=100)
    schedule_template = models.ForeignKey(
        ScheduleTemplate, blank=False, null=False, on_delete=models.CASCADE
    )
    day = models.CharField(choices=Day.choices, max_length=32)

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
        verbose_name_plural = "shift slot group templates"


class ShiftSlotTemplate(models.Model):
    class Meta:
        verbose_name_plural = "shift slot templates"
        unique_together = (
            (
                "shift_template",
                "role",
            ),
        )

    shift_template = models.ForeignKey(
        ShiftTemplate, blank=False, null=False, on_delete=models.CASCADE
    )
    role = models.ForeignKey(
        ScheduleRole, blank=False, null=False, on_delete=models.CASCADE
    )
    count = models.IntegerField()

    def __str__(self):
        return "Template for ShiftSlot %s for shift-template %s" % (
            self.role.name,
            self.shift_template.name,
        )
