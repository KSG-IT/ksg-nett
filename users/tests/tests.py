# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import re
import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from users.models import UsersHaveMadeOut, User
from users.tests.factories import UserFactory, UsersHaveMadeOutFactory
from users.views import user_detail, klinekart

from organization.consts import InternalGroupPositionMembershipType


class UserProfileTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        # Delete the temporary media root
        shutil.rmtree(cls.temp_media_root)
        # Restore
        settings.MEDIA_ROOT = "/media/"

    @classmethod
    def setUpClass(cls):
        # Set up mocking of the media root temporarily so we can create uploads
        cls.temp_media_root = tempfile.mkdtemp()
        settings.MEDIA_ROOT = cls.temp_media_root

    def test_str_and_repr_should_not_crash(self):
        self.user = UserFactory()
        str_representation = str(self.user)
        repr_representation = repr(self.user)

        self.assertIsInstance(str_representation, str)
        self.assertIsInstance(repr_representation, str)

    def test_get_start_ksg_display__user_in_spring__returns_v_prefix_and_correct_year(
        self,
    ):
        user = UserFactory()
        user.start_ksg = timezone.datetime(year=2018, month=3, day=1)
        user.save()
        self.assertEqual(user.get_start_ksg_display(), "V18")

    def test_get_start_ksg_display__user_in_autumn__returns_h_prefix_and_correct_year(
        self,
    ):
        user = UserFactory()
        user.start_ksg = timezone.datetime(year=2018, month=8, day=1)
        user.save()
        self.assertEqual(user.get_start_ksg_display(), "H18")


class UsersHaveMadeOutModelTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.user_two = UserFactory()
        self.user_three = UserFactory()

    def test_str_and_repr__does_not_crash(self):
        made_out = UsersHaveMadeOutFactory(user_one=self.user, user_two=self.user_two)
        str(made_out)
        repr(made_out)


class UsersHaveMadeOutManagerTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.user_two = UserFactory()
        self.user_three = UserFactory()
        self.made_out_this_semester = UsersHaveMadeOutFactory(
            user_one=self.user,
            user_two=self.user_two,
        )
        now = timezone.now()
        self.made_out_in_spring_last_year = UsersHaveMadeOutFactory(
            user_one=self.user,
            user_two=self.user_two,
            created=now.replace(year=now.year - 1, month=3, day=1),
        )
        self.made_out_in_autumn_last_year = UsersHaveMadeOutFactory(
            user_one=self.user,
            user_two=self.user_two,
            created=now.replace(year=now.year - 1, month=9, day=1),
        )

    def test_this_semester__returns_made_outs_from_this_semester(self):
        this_semester_made_outs = UsersHaveMadeOut.objects.this_semester()
        self.assertEqual(this_semester_made_outs.count(), 1)
        self.assertEqual(this_semester_made_outs.first(), self.made_out_this_semester)

    def test_in_semester__this_semester_as_input__returns_made_outs_from_this_semester(
        self,
    ):
        made_outs = UsersHaveMadeOut.objects.in_semester(
            self.made_out_this_semester.created
        )
        self.assertEqual(made_outs.count(), 1)
        self.assertEqual(made_outs.first(), self.made_out_this_semester)

    def test_in_semester__specific_semester_in_spring_as_input__only_returns_relevant_made_outs(
        self,
    ):
        made_outs = UsersHaveMadeOut.objects.in_semester(
            self.made_out_in_spring_last_year.created
        )
        self.assertEqual(made_outs.count(), 1)
        self.assertEqual(made_outs.first(), self.made_out_in_spring_last_year)

    def test_in_semester__specific_semester_in_autumn_as_input__only_returns_relevant_made_outs(
        self,
    ):
        made_outs = UsersHaveMadeOut.objects.in_semester(
            self.made_out_in_autumn_last_year.created
        )
        self.assertEqual(made_outs.count(), 1)
        self.assertEqual(made_outs.first(), self.made_out_in_autumn_last_year)


class KlineKartViewTest(TestCase):
    def setUp(self):
        self.user = UserFactory.create(anonymize_in_made_out_map=False)
        self.user.set_password("password")
        self.user.save()

        self.user_two = UserFactory.create(anonymize_in_made_out_map=False)
        self.user_three = UserFactory.create(anonymize_in_made_out_map=True)
        self.user_four = UserFactory.create(anonymize_in_made_out_map=True)
        self.client.login(username=self.user.username, password="password")

    def test_klinekart__renders_the_klinekart_template(self):
        response = self.client.get(reverse(klinekart))
        self.assertTemplateUsed(response, "users/klinekart.html")

    def test_klinekart__with_associations__sends_all_associations_properly_as_json(
        self,
    ):
        UsersHaveMadeOut.objects.create(
            user_one=self.user,
            user_two=self.user_two,
        )
        UsersHaveMadeOut.objects.create(
            user_one=self.user_two,
            user_two=self.user_three,
        )
        UsersHaveMadeOut.objects.create(
            user_one=self.user_three,
            user_two=self.user,
        )
        UsersHaveMadeOut.objects.create(
            user_one=self.user_four,
            user_two=self.user_two,
        )
        UsersHaveMadeOut.objects.create(
            user_one=self.user_four,
            user_two=self.user_three,
        )
        # Duplicates are allowed
        UsersHaveMadeOut.objects.create(
            user_one=self.user_two,
            user_two=self.user,
        )

        response: HttpResponse = self.client.get(reverse(klinekart))
        self.assertTemplateUsed(response, "users/klinekart.html")

        data = json.loads(response.context["made_out_data"])
        self.assertEqual(len(data), 6)

        ids = set()
        names = set()
        imgs = set()

        for tuple in data:
            ids.add(tuple[0]["id"])
            ids.add(tuple[1]["id"])

            names.add(tuple[0]["name"])
            names.add(tuple[1]["name"])

            imgs.add(tuple[0]["img"])
            imgs.add(tuple[1]["img"])

        self.assertTrue(ids == {1, 2, -1, -2})
        self.assertTrue(
            names
            == {self.user.get_full_name(), self.user_two.get_full_name(), "Anonymous"}
        )
        self.assertTrue(
            imgs == {self.user.profile_image.url, self.user_two.profile_image.url, None}
        )
