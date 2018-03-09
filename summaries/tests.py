from urllib.parse import urlencode

from django.test import TestCase

# Create your tests here.
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from summaries.consts import SUMMARY_TYPE_BS
from summaries.models import Summary
from summaries.views import summaries_delete, summaries_create, summaries_update, summaries_list
from users.models import User


class TestSummaryModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = [
            User(username='user_one', email='user_one@example.com'),
            User(username='user_two', email='user_two@example.com'),
            User(username='user_three', email='user_three@example.com')
        ]
        for user in cls.users:
            user.save()
        cls.summary = Summary(
            summary_type=SUMMARY_TYPE_BS,
            contents="Kjersti falt av stolen.",
            date=timezone.now(),
            reporter=cls.users[0]
        )
        cls.summary.save()
        cls.summary.participants.add(*cls.users)
        cls.summary.save()

    def test_str_and_repr_does_not_fail(self):
        str(self.summary)
        repr(self.summary)


class SummaryPresentationViewsTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User(
            username='test',
            email='test@example.com'
        )
        cls.user.set_password('password')
        cls.user.save()
        Summary.objects.bulk_create([
            Summary(summary_type=SUMMARY_TYPE_BS, contents='Summary', reporter=cls.user, date=timezone.now()),
            Summary(summary_type=SUMMARY_TYPE_BS, contents='Summary', reporter=cls.user, date=timezone.now()),
            Summary(summary_type=SUMMARY_TYPE_BS, contents='Summary', reporter=cls.user, date=timezone.now()),
            Summary(summary_type=SUMMARY_TYPE_BS, contents='Summary', reporter=cls.user, date=timezone.now())
        ])

    def test_list_view__renders_a_template_with_context(self):
        self.client.login(username='test', password='password')
        response = self.client.get(reverse(summaries_list))
        self.assertEqual(response.context['summaries'].count(), 4)
        self.assertTemplateUsed(response, 'summaries/summaries_list.html')


class SummaryCreateTest(TestCase):

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

    def test_GET_request__renders_a_template(self):
        response = self.client.get(reverse(summaries_create))
        self.assertTemplateUsed(response, 'summaries/summaries_create.html')

    def test_summary_create__POST_request_with_data__creates_new_summary(self):
        response = self.client.post(reverse(summaries_create), urlencode({
            'summary_type': 'bs',
            'contents': 'Nice summary yo',
            'reporter': self.user.id,
            'date': timezone.now().strftime("%Y-%m-%d")
        }), content_type="application/x-www-form-urlencoded")
        self.assertEqual(response.status_code, 302)
        summary = Summary.objects.first()
        self.assertIsNotNone(summary)
        self.assertEqual(summary.contents, 'Nice summary yo')
        self.assertEqual(summary.reporter, self.user)

    def test_summary_create__POST_request_with_missing_data__renders_form_with_error(elf):
        response = self.client.post(reverse(summaries_create), {
            'text': 'This is a cool summary'
        })
        # We're missing a field
        self.assertIn("This field is required", response.content.decode("utf-8"))

    def test_summary_create__bad_http_method__fails_with_405(self):
        response = self.client.delete(reverse(summaries_create))
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

