import pytz
from factory import Faker, RelatedFactory, SubFactory
from factory.django import DjangoModelFactory
from ksg_nett import settings
from summaries.models import Summary


class SummaryFactory(DjangoModelFactory):
    class Meta:
        model = Summary

    contents = Faker("text")
    participants = RelatedFactory("users.tests.factories.UserFactory")
    reporter = SubFactory("users.tests.factories.UserFactory")
    date = Faker("past_datetime", tzinfo=pytz.timezone(settings.TIME_ZONE))
