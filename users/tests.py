# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase


# Create your tests here.
from django.utils import timezone

from users.models import UserProfile


class UserProfileTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user_1 = User(
            username='username'
        )
        cls.user_1.save()
        cls.user_profile_1 = UserProfile(
            user=cls.user_1,
            name="Ola Nordmann",
            date_of_birth=timezone.now(),
            study='Gløshaugen',
            email='ola@nordmann.com',
            phone=19393113,
            study_address='Kråkeveien 5',
            home_address='Kråkeveien 4',
            start_ksg=timezone.now()
        )
        cls.user_profile_1.save()

    def test_create_without_user_should_fail(self):
        with self.assertRaises(IntegrityError):
            user_profile_2 = UserProfile(
                name="Ola Nordmann",
                date_of_birth=timezone.now(),
                study='Gløshaugen',
                email='ola@nordmann.com',
                phone=19393113,
                study_address='Kråkeveien 5',
                home_address='Kråkeveien 4',
                start_ksg=timezone.now()
            )
            user_profile_2.save()

    def test_str_and_repr_should_not_crash(self):
        str_representation = str(self.user_profile_1)
        repr_representation = repr(self.user_profile_1)

        self.assertIsInstance(str_representation, str)
        self.assertIsInstance(repr_representation, str)

