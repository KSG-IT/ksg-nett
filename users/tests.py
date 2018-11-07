# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import shutil
import tempfile

from unittest import mock

from coreapi.utils import File
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

# Create your tests here.
from django.utils import timezone

from commissions.models import Commission
from users.models import User, KSG_STATUS_TYPES


class UserProfileTest(TestCase):

    @classmethod
    def tearDownClass(cls):
        # Delete the temporary media root
        shutil.rmtree(cls.temp_media_root)
        # Restore
        settings.MEDIA_ROOT = "/media/"

    @classmethod
    def setUpTestData(cls):
        # Set up mocking of the media root temporarily so we can create uploads
        cls.temp_media_root = tempfile.mkdtemp()
        settings.MEDIA_ROOT = cls.temp_media_root

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

    def test_get_start_ksg_display__user_in_spring__returns_v_prefix_and_correct_year(self):
        user = User.objects.create(
            username='username2',
            email='user2@example.com',
            start_ksg=timezone.datetime(year=2018, month=3, day=1)
        )
        user.start_ksg = timezone.datetime(year=2018, month=3, day=1)
        user.save()
        self.assertEqual(user.get_start_ksg_display(), "V18")

    def test_get_start_ksg_display__user_in_autumn__returns_h_prefix_and_correct_year(self):
        user = User.objects.create(
            username='username2',
            email='user2@example.com',
            start_ksg=timezone.datetime(year=2018, month=3, day=1)
        )
        user.start_ksg = timezone.datetime(year=2018, month=8, day=1)
        user.save()
        self.assertEqual(user.get_start_ksg_display(), "H18")

    def test_profile_image_url__no_image__returns_none(self):
        user = User.objects.create(
            username='username2',
            email='user2@example.com'
        )
        self.assertEqual(user.profile_image_url, None)

    def test_profile_image_url__image_exists__returns_url(self):
        user = User.objects.create(
            username='username2',
            email='user2@example.com'
        )
        image_file = SimpleUploadedFile(name="test_image.jpeg", content=b'', content_type='image/jpeg')
        user.profile_image = image_file
        user.save()
        self.assertEqual(user.profile_image_url, '/media/profiles/test_image.jpeg')

    def test_active__status_is_active__returns_true(self):
        user = User.objects.create(
            username='username2' ,
            email='user2@example.com',
            ksg_status=KSG_STATUS_TYPES[0][0]
        )
        self.assertEqual(user.active(), True)

    def test_active__status_is_not_active__returns_false(self):
        user = User.objects.create(
            username='username2' ,
            email='user2@example.com',
            ksg_status=KSG_STATUS_TYPES[1][0]
        )
        self.assertEqual(user.active(), False)
        user.ksg_status = KSG_STATUS_TYPES[2][0]
        user.save()
        self.assertEqual(user.active(), False)
        user.ksg_status = KSG_STATUS_TYPES[3][0]
        user.save()
        self.assertEqual(user.active(), False)

