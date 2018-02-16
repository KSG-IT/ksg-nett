from django.test import TestCase

# Create your tests here.
from django.utils import timezone

from summaries.consts import SUMMARY_TYPE_BS
from summaries.models import Summary
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

