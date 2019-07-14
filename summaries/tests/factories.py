import random

import pytz
from factory import DjangoModelFactory, Faker, RelatedFactory, SubFactory

from ksg_nett import settings
from summaries.consts import SUMMARY_TYPE_SHORT_NAMES
from summaries.models import Summary


class SummaryFactory(DjangoModelFactory):
    class Meta:
        model = Summary

    summary_type = random.choice(list(SUMMARY_TYPE_SHORT_NAMES))[0]
    contents = Faker('text')
    participants = RelatedFactory('users.tests.factories.UserFactory')
    reporter = SubFactory('users.tests.factories.UserFactory')
    date = Faker('past_datetime', tzinfo=pytz.timezone(settings.TIME_ZONE))
