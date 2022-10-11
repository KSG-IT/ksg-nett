from urllib.parse import urlencode

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from summaries.consts import SummaryType
from summaries.models import Summary
from summaries.tests.factories import SummaryFactory
from summaries.views import (
    summaries_delete,
    summaries_create,
    summaries_update,
    summaries_list,
)
from users.tests.factories import UserFactory


class TestSummaryModel(TestCase):
    def setUp(self):
        self.summary = SummaryFactory(
            type=SummaryType.BARSJEF, contents="Kjersti falt av stolen! 😂"
        )

    def test_str_and_repr_does_not_fail(self):
        str(self.summary)
        repr(self.summary)
