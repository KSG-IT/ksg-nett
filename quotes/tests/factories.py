import random
import pytz
from users.tests.factories import UserFactory
from ksg_nett import settings
from factory import Faker, SubFactory
from factory.django import DjangoModelFactory
from factory import post_generation


from quotes.models import Quote, QuoteVote


class QuoteFactory(DjangoModelFactory):
    class Meta:
        model = Quote

    text = Faker("text")
    verified_by = SubFactory(UserFactory)
    reported_by = SubFactory(UserFactory)

    @post_generation
    def tagged(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of groups were passed in, use them
            for user in extracted:
                self.tagged.add(user)
        else:
            self.tagged.set(UserFactory.create_batch(2))

    created_at = Faker("past_datetime", tzinfo=pytz.timezone(settings.TIME_ZONE))


class QuoteVoteFactory(DjangoModelFactory):
    class Meta:
        model = QuoteVote

    quote = SubFactory(QuoteFactory)
    value = random.choice([-1, 1])
    caster = SubFactory(UserFactory)
