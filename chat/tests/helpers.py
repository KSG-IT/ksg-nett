import datetime
from zoneinfo import ZoneInfo

from django.conf import settings

from schedules.models import RoleOption
from schedules.tests.factories import ShiftFactory, ShiftSlotFactory
from users.tests.factories import UserFactory

LOCAL = ZoneInfo(settings.TIME_ZONE)
# A Friday evening
FRIDAY_19 = datetime.datetime(2026, 10, 16, 19, 0, tzinfo=LOCAL)
SATURDAY_02 = datetime.datetime(2026, 10, 17, 2, 0, tzinfo=LOCAL)


def make_shift(user_count=3, start=None, end=None, name="Bar fredag", **kwargs):
    """A shift 18:00 to 02:00 with `user_count` filled slots. Returns (shift, users)."""
    shift = ShiftFactory.create(
        name=name,
        datetime_start=start or datetime.datetime(2026, 10, 16, 18, 0, tzinfo=LOCAL),
        datetime_end=end or SATURDAY_02,
        **kwargs,
    )
    users = [UserFactory.create() for _ in range(user_count)]
    for user in users:
        ShiftSlotFactory.create(shift=shift, user=user, role=RoleOption.BARTENDER)
    return shift, users
