from django.test import TestCase
from factory import Iterator
from quotes.models import Quote
from quotes.tests.factories import QuoteFactory, QuoteVoteFactory
from users.tests.factories import UserFactory


class QuoteModelTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.user_two = UserFactory()
        self.quote = QuoteFactory()
        self.quote_without_votes = QuoteFactory()
        QuoteVoteFactory.create_batch(
            4,
            quote=self.quote,
            caster=Iterator(UserFactory.create_batch(4)),
            value=Iterator([1, -1, 1, 1]),
        )

    def test_str_and_repr_should_not_fail(self):
        str(self.quote)
        repr(self.quote)

    def test_sum_should_return_0_when_no_votes_exist(self):
        self.assertEqual(self.quote_without_votes.sum, 0)

    def test_sum_should_return_correct_when_votes_exist(self):
        self.assertEqual(self.quote.sum, 2)

        QuoteVoteFactory(quote=self.quote, caster=self.user, value=-1)
        self.assertEqual(self.quote.sum, 1)


class QuoteVoteModelTest(TestCase):
    def setUp(self):
        self.quote_vote = QuoteVoteFactory()

    def test_str_and_repr_should_not_fail(self):
        str(self.quote_vote)
        repr(self.quote_vote)
        # The __str__ method changes on positive and negative values
        # so we need to test positive as well
        self.quote_vote.value = 1
        self.quote_vote.save()

        str(self.quote_vote)


class QuoteManagersTest(TestCase):
    def setUp(self):
        self.verified_quotes = QuoteFactory.create_batch(2, approved=True)
        self.unverified_quotes = QuoteFactory.create_batch(4, approved=False)

    def test_quote_pending_objects__returns_correct_count(self):
        self.assertEqual(Quote.get_pending_quotes().count(), 4)

    def test_quote_verified_objects__returns_correct_count(self):
        self.assertEqual(Quote.get_approved_quotes().count(), 2)
