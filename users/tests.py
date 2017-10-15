# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

# Create your tests here.
from django.utils import timezone

from users.models import User


class UserProfileTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_1 = User(
            username='username',
            first_name="Ola",
            last_name="Nordmann",
            date_of_birth=timezone.now(),
            study='Gløshaugen',
            email='ola@nordmann.com',
            phone=19393113,
            study_address='Kråkeveien 5',
            home_address='Kråkeveien 4'
        )
        cls.user_1.save()

    def test_str_and_repr_should_not_crash(self):
        str_representation = str(self.user_1)
        repr_representation = repr(self.user_1)

        self.assertIsInstance(str_representation, str)
        self.assertIsInstance(repr_representation, str)
