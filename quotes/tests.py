from django.test import TestCase

# Create your tests here.
from django.utils import timezone

from quotes.models import Quote, QuoteVote
from users.models import User


class QuoteModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User(
            username='test',
            email='test@example.com'
        )
        cls.user.save()
        cls.quote = Quote(
            text='Lorem Ipsum',
            quoter=cls.user
        )
        cls.quote.save()
        QuoteVote.objects.bulk_create([
            QuoteVote(quote=cls.quote, caster=cls.user, value=1),
            QuoteVote(quote=cls.quote, caster=cls.user, value=-1),
            QuoteVote(quote=cls.quote, caster=cls.user, value=1),
            QuoteVote(quote=cls.quote, caster=cls.user, value=1),
        ])

    def test_str_and_repr_should_not_fail(self):
        str(self.quote)
        repr(self.quote)

    def test_sum_should_return_correct(self):
        self.assertEqual(self.quote.sum, 2)

        QuoteVote(
            quote=self.quote,
            caster=self.user,
            value=-1
        ).save()
        self.assertEqual(self.quote.sum, 1)


class QuoteVoteModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User(
            username='test',
            email='test@example.com'
        )
        cls.user.save()
        cls.quote = Quote(
            text='Lorem Ipsum',
            quoter=cls.user
        )
        cls.quote.save()
        cls.quote_vote = QuoteVote(
            quote=cls.quote,
            value=-1,
            caster=cls.user
        )
        cls.quote_vote.save()

    def test_str_and_repr_should_not_fail(self):
        str(self.quote_vote)
        repr(self.quote_vote)
