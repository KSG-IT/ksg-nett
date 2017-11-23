from django.test import TestCase

# Create your tests here.
from django.urls import reverse
from django.utils import timezone

from quotes.models import Quote, QuoteVote
from quotes.views import list_view, vote_up
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
        cls.quote_without_votes = Quote(
            text='Lorem Ipsum',
            quoter=cls.user
        )
        cls.quote_without_votes.save()
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

    def test_sum_should_return_0_when_no_votes_exist(self):
        self.assertEqual(self.quote_without_votes.sum, 0)

    def test_sum_should_return_correct_when_votes_exist(self):
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


class QuoteManagersTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User(
            username='test',
            email='test@example.com'
        )
        cls.user.save()
        Quote.objects.bulk_create([
            Quote(text='Quote', quoter=cls.user),
            Quote(text='Quote', quoter=cls.user),
            Quote(text='Quote', quoter=cls.user, verified_by=cls.user),
            Quote(text='Quote', quoter=cls.user),
            Quote(text='Quote', quoter=cls.user),
            Quote(text='Quote', quoter=cls.user, verified_by=cls.user),
        ])

    def test_quote_pending_objects_works(self):
        self.assertEqual(Quote.pending_objects.count(), 4)

    def test_quote_verified_objects_works(self):
        self.assertEqual(Quote.verified_objects.count(), 2)


class QuoteViewsTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User(
            username='test',
            email='test@example.com'
        )
        cls.user.set_password('password')
        cls.user.save()
        Quote.objects.bulk_create([
            Quote(text='Quote', quoter=cls.user),
            Quote(text='Quote', quoter=cls.user, verified_by=cls.user),
            Quote(text='Quote', quoter=cls.user, verified_by=cls.user),
            Quote(text='Quote', quoter=cls.user, verified_by=cls.user),
        ])

        QuoteVote.objects.bulk_create([
            QuoteVote(caster=cls.user, quote_id=3, value=1),
            QuoteVote(caster=cls.user, quote_id=4, value=-1)
        ])

    def test_list_view(self):
        response = self.client.get(reverse(list_view))
        self.assertEqual(response.context['pending'].count(), 1)
        self.assertEqual(response.context['quotes'].count(), 3)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'quotes/quotes_list.html')

    def test_vote_up_user_has_not_voted_yet(self):
        self.client.login(username='test', password='password')
        response = self.client.post(reverse(vote_up, kwargs={'quote_id': 2}))
        self.assertEqual(response.status_code, 200)
        quote = Quote.objects.get(pk=2)
        self.assertEqual(quote.sum, 1)

    def test_vote_up_has_voted_down_already(self):
        # Test that sum updates when we change vote from down to up
        self.client.login(username='test', password='password')
        quote = Quote.objects.get(pk=4)
        self.assertEqual(quote.sum, -1)
        response = self.client.post(reverse(vote_up, kwargs={'quote_id': 4}))
        self.assertEqual(response.status_code, 200)
        quote.refresh_from_db()
        self.assertEqual(quote.sum, 1)

    def test_vote_up_has_voted_up_already(self):
        # Test that sum stays the same
        self.client.login(username='test', password='password')
        quote = Quote.objects.get(pk=3)
        self.assertEqual(quote.sum, 1)
        response = self.client.post(reverse(vote_up, kwargs={'quote_id': 3}))
        self.assertEqual(response.status_code, 200)
        quote.refresh_from_db()
        self.assertEqual(quote.sum, 1)

    def test_vote_up_pending_fails(self):
        self.client.login(username='test', password='password')
        response = self.client.post(reverse(vote_up, kwargs={'quote_id': 1}))
        self.assertEqual(response.status_code, 404)
