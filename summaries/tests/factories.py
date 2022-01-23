import random

import pytz
from factory import Faker, RelatedFactory, SubFactory
from factory.django import DjangoModelFactory


from ksg_nett import settings
from summaries.consts import SummaryType
from summaries.models import Summary


class SummaryFactory(DjangoModelFactory):
    class Meta:
        model = Summary

    type = random.choice(SummaryType.values)[0]
    contents = Faker("text")
    participants = RelatedFactory("users.tests.factories.UserFactory")
    reporter = SubFactory("users.tests.factories.UserFactory")
    date = Faker("past_datetime", tzinfo=pytz.timezone(settings.TIME_ZONE))
