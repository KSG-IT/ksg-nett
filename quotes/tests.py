from urllib.parse import urlencode

from django.test import TestCase

# Create your tests here.
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from quotes.models import Quote, QuoteVote
from quotes.views import quotes_list, vote_up, vote_down, quotes_add, quotes_edit, quotes_delete
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
        # The __str__ method changes on positive and negative values
        # so we need to test positive as well
        self.quote_vote.value = 1
        self.quote_vote.save()

        str(self.quote_vote)


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

    def test_quote_pending_objects__returns_correct_count(self):
        self.assertEqual(Quote.pending_objects.count(), 4)

    def test_quote_verified_objects__returns_correct_count(self):
        self.assertEqual(Quote.verified_objects.count(), 2)


class QuotePresentationViewsTest(TestCase):

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

    def test_list_view__renders_template_with_correct_context(self):
        self.client.login(username='test', password='password')
        response = self.client.get(reverse(quotes_list))
        self.assertEqual(response.context['pending'].count(), 1)
        self.assertEqual(response.context['quotes'].count(), 3)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'quotes/quotes_list.html')


class QuoteVoteUpTest(TestCase):

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

    def test_vote_up__user_has_not_voted_yet__quote_sum_changes(self):
        self.client.login(username='test', password='password')
        response = self.client.post(reverse(vote_up, kwargs={'quote_id': 2}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        quote = Quote.objects.get(pk=2)
        self.assertEqual(quote.sum, 1)

    def test_vote_up__user_has_voted_down_already__quote_sum_changes(self):
        self.client.login(username='test', password='password')
        quote = Quote.objects.get(pk=4)
        self.assertEqual(quote.sum, -1)
        response = self.client.post(reverse(vote_up, kwargs={'quote_id': 4}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        quote.refresh_from_db()
        self.assertEqual(quote.sum, 1)

    def test_vote_up__user_has_voted_up_already__quote_sum_does_not_change(self):
        self.client.login(username='test', password='password')
        quote = Quote.objects.get(pk=3)
        self.assertEqual(quote.sum, 1)
        response = self.client.post(reverse(vote_up, kwargs={'quote_id': 3}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        quote.refresh_from_db()
        self.assertEqual(quote.sum, 1)

    def test_vote_up__quote_is_pending__fails_with_404(self):
        self.client.login(username='test', password='password')
        response = self.client.post(reverse(vote_up, kwargs={'quote_id': 1}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_vote_up__bad_http_method__fails_with_405(self):
        self.client.login(username='test', password='password')
        response = self.client.get(reverse(vote_up, kwargs={'quote_id': 2}))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class QuoteVoteDownTest(TestCase):

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

    def test_vote_down__user_has_not_voted_yet__quote_sum_changes(self):
        self.client.login(username='test', password='password')
        response = self.client.post(reverse(vote_down, kwargs={'quote_id': 2}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        quote = Quote.objects.get(pk=2)
        self.assertEqual(quote.sum, -1)

    def test_vote_down__user_has_voted_down_already__quote_sum_does_not_change(self):
        # Test that sum stays the same
        self.client.login(username='test', password='password')
        quote = Quote.objects.get(pk=4)
        self.assertEqual(quote.sum, -1)
        response = self.client.post(reverse(vote_down, kwargs={'quote_id': 4}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        quote.refresh_from_db()
        self.assertEqual(quote.sum, -1)

    def test_vote_down__user_has_voted_up_already__quote_sum_changes(self):
        self.client.login(username='test', password='password')
        quote = Quote.objects.get(pk=3)
        self.assertEqual(quote.sum, 1)
        response = self.client.post(reverse(vote_down, kwargs={'quote_id': 3}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        quote.refresh_from_db()
        self.assertEqual(quote.sum, -1)

    def test_vote_down__quote_is_pending__fails_with_404(self):
        self.client.login(username='test', password='password')
        response = self.client.post(reverse(vote_down, kwargs={'quote_id': 1}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_vote_down__bad_http_method__fails_with_405(self):
        self.client.login(username='test', password='password')
        response = self.client.get(reverse(vote_down, kwargs={'quote_id': 2}))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class QuoteAddTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User(
            username='test',
            email='test@example.com'
        )
        cls.user.set_password('password')
        cls.user.save()

    def setUp(self):
        self.client.login(username='test', password='password')

    def test_quote_add__GET_request___renders_template(self):
        response = self.client.get(reverse(quotes_add))
        self.assertTemplateUsed(response, 'quotes/quotes_add.html')

    def test_quote_add__POST_request_with_new_quote__creates_quote(self):
        self.client.post(reverse(quotes_add), urlencode({
            'text': 'This is a cool quote',
            'quoter': self.user.id
        }), content_type="application/x-www-form-urlencoded")
        quote = Quote.objects.first()
        self.assertIsNotNone(quote)
        self.assertEqual(quote.text, 'This is a cool quote')
        self.assertEqual(quote.quoter, self.user)

    def test_quote_add__POST_request_with_missing_data__renders_with_form_failure(self):
        response = self.client.post(reverse(quotes_add), {
            'text': 'This is a cool quote'
            # Missing id
        })
        # We're missing a field
        self.assertIn("This field is required", response.content.decode("utf-8"))

    def test_quotes_add__bad_http_method__fails_with_405(self):
        response = self.client.delete(reverse(quotes_add))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class QuoteEditTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User(
            username='test',
            email='test@example.com'
        )
        cls.user.set_password('password')
        cls.user.save()

        cls.quote = Quote(
            text='Some quote text',
            quoter=cls.user
        )
        cls.quote.save()

    def setUp(self):
        self.client.login(username='test', password='password')

    def test_quotes_edit__GET_request__renders_template(self):
        response = self.client.get(reverse(quotes_edit, kwargs={'quote_id': 1}))
        self.assertTemplateUsed(response, 'quotes/quotes_edit.html')

    def test_quotes_edit__POST_request_with_new_quote_data__changes_quote_object(self):
        self.client.post(reverse(quotes_edit, kwargs={'quote_id': 1}), urlencode({
            'text': 'Some new quote text',
            'quoter': self.user.id
        }), content_type="application/x-www-form-urlencoded")
        quote = Quote.objects.first()
        self.assertEqual(Quote.objects.count(), 1)
        self.assertIsNotNone(quote)
        self.assertEqual(quote.text, 'Some new quote text')
        self.assertEqual(quote.quoter, self.user)

    def test_quote_edit__POST_request_with_missing_data__renders_with_form_failure(self):
        response = self.client.post(reverse(quotes_edit, kwargs={'quote_id': 1}), urlencode({
            'text': 'Some new quote text',
        }), content_type="application/x-www-form-urlencoded")
        self.assertIn("This field is required", response.content.decode("utf-8"))

    def test_quotes_edit__bad_http_method__fails_with_405(self):
        response = self.client.delete(reverse(quotes_edit, kwargs={'quote_id': 1}), urlencode({
            'text': 'Some new quote text',
        }), content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class QuoteDeleteTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User(
            username='test',
            email='test@example.com'
        )
        cls.user.set_password('password')
        cls.user.save()

        cls.quote = Quote(
            text='Some quote text',
            quoter=cls.user
        )
        cls.quote.save()

    def setUp(self):
        self.client.login(username='test', password='password')

    def test_delete_quote__deletes_quote(self):
        response = self.client.post(reverse(quotes_delete, kwargs={'quote_id': 1}))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_delete_quote__non_existing_quote__fails_with_404(self):
        response = self.client.post(reverse(quotes_delete, kwargs={'quote_id': 2}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_quote__bad_http_method__fails_with_405(self):
        response = self.client.put(reverse(quotes_delete, kwargs={'quote_id': 2}))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

