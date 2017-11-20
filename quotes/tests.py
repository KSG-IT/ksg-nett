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
        User.objects.bulk_create([
            User(username='user%d' % 1, email='user%d@example.com' % 1),
            User(username='user%d' % 2, email='user%d@example.com' % 2),
            User(username='user%d' % 3, email='user%d@example.com' % 3),
            User(username='user%d' % 4, email='user%d@example.com' % 4),
        ])
        QuoteVote.objects.bulk_create([
            QuoteVote(quote=cls.quote, caster_id=cls.user.id+1, value=1),
            QuoteVote(quote=cls.quote, caster_id=cls.user.id+2, value=-1),
            QuoteVote(quote=cls.quote, caster_id=cls.user.id+3, value=1),
            QuoteVote(quote=cls.quote, caster_id=cls.user.id+4, value=1),
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
