import random
import pytz
from users.tests.factories import UserFactory
from ksg_nett import settings
from factory import DjangoModelFactory, Faker, SubFactory

from quotes.models import Quote, QuoteVote


class QuoteFactory(DjangoModelFactory):
    class Meta:
        model = Quote

    text = Faker('text')
    quoter = SubFactory('users.tests.factories.UserFactory')
    verified_by = SubFactory('users.tests.factories.UserFactory')
    reported_by = SubFactory(UserFactory)
    # created_at = Faker('past_datetime', tzinfo=pytz.timezone(settings.TIME_ZONE))


class QuoteVoteFactory(DjangoModelFactory):
    class Meta:
        model = QuoteVote

    quote = SubFactory(QuoteFactory)
    value = random.choice([-1, 1])
    caster = SubFactory('users.tests.factories.UserFactory')
