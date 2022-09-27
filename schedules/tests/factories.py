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
    ShiftSlotTemplate,
    ShiftTrade,
)
