# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
# Create your tests here.
from django.urls import reverse
from django.utils import timezone

from users.models import User, KSG_STATUS_TYPES
from users.views import user_detail


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


class UserDetailViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User(
            username='username',
            email='user@example.com',
            first_name='Tormod',
            last_name='Haugland'
        )
        cls.user.set_password('password')
        cls.user.save()
        cls.user_detail_url = reverse(user_detail, kwargs={'user_id': cls.user.id})

    def test_user_detail__not_logged_in__redirects(self):
        response = self.client.get(self.user_detail_url)
        self.assertEqual(response.status_code, 302)

    def test_user_detail__logged_in_user_does_not_exist__returns_404_not_found(self):
        self.client.login(
            username='username',
            password='password'
        )
        response = self.client.get(reverse(user_detail, kwargs={'user_id': 1337}))
        self.assertEqual(response.status_code, 404)

    def test_user_detail__logged_in_user_exists__renders_profile_page(self):
        self.client.login(
            username='username',
            password='password'
        )
        response = self.client.get(reverse(user_detail, kwargs={'user_id': self.user.id}))
        # Decode so we can do string-comparison/containment checks
        content = response.content.decode()
        self.assertTemplateUsed(response, 'users/profile_page.html')

        # Check that some key properties of the user is rendered
        self.assertIn(self.user.get_full_name(), content)
        self.assertIn(self.user.get_start_ksg_display(), content)
        self.assertIn(self.user.email, content)
        self.assertIn(self.user.phone, content)

