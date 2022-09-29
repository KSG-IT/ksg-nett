import random
from datetime import timedelta, datetime, date

import pytz
from django.utils import timezone
from factory import Faker, SubFactory, RelatedFactory, LazyAttribute, SelfAttribute
from factory.django import DjangoModelFactory

from ksg_nett import settings
from schedules.models import (
    Schedule,
    ShiftSlot,
    Shift,
    ScheduleTemplate,
    ShiftTemplate,
    ShiftSlotTemplate,
    ShiftTrade,
)


class ScheduleFactory(DjangoModelFactory):
    class Meta:
        model = Schedule

    name = Faker("name")


class ScheduleTemplateFactory(DjangoModelFactory):
    class Meta:
        model = ScheduleTemplate

    name = Faker("name")
    schedule = SubFactory(ScheduleFactory)


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

"""


class ShiftTemplateFactory(DjangoModelFactory):
    class Meta:
        model = ShiftTemplate

    name = Faker("name")
    schedule_template = SubFactory(ScheduleTemplateFactory)
    # random choice from the choices
    location = LazyAttribute(
        lambda o: random.choice([location[0] for location in Shift.Location.choices])
    )
    day = LazyAttribute(
        lambda o: random.choice([day[0] for day in ShiftTemplate.Day.choices])
    )
    time_start = LazyAttribute(
        lambda o: timezone.now().time() + timedelta(hours=random.randint(0, 24))
    )
    time_end = LazyAttribute(
        lambda o: timezone.now().time() + timedelta(hours=random.randint(0, 24))
    )


class ShiftSlotTemplateFactory(DjangoModelFactory):
    class Meta:
        model = ShiftSlotTemplate

    shift_template = SubFactory(ShiftTemplateFactory)
    role = LazyAttribute(
        lambda o: random.choice([x[0] for x in ShiftSlot.RoleOption.choices])
    )
    count = LazyAttribute(lambda o: random.randint(1, 5))
