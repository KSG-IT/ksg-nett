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

from users.forms.user_form import UserForm
from users.models import KSG_STATUS_TYPES, UsersHaveMadeOut
from users.tests.factories import UserFactory, UsersHaveMadeOutFactory
from users.views import user_detail, update_user, klinekart


class UserProfileTest(TestCase):

    @classmethod
    def tearDownClass(cls):
        super(UserProfileTest, cls).tearDownClass()
        # Delete the temporary media root
        shutil.rmtree(cls.temp_media_root)
        # Restore
        settings.MEDIA_ROOT = "/media/"

    @classmethod
    def setUpTestData(cls):
        # Set up mocking of the media root temporarily so we can create uploads
        cls.temp_media_root = tempfile.mkdtemp()
        settings.MEDIA_ROOT = cls.temp_media_root

    def test_str_and_repr_should_not_crash(self):
        self.user = UserFactory()
        str_representation = str(self.user)
        repr_representation = repr(self.user)

        self.assertIsInstance(str_representation, str)
        self.assertIsInstance(repr_representation, str)

    def test_get_start_ksg_display__user_in_spring__returns_v_prefix_and_correct_year(self):
        user = UserFactory()
        user.start_ksg = timezone.datetime(year=2018, month=3, day=1)
        user.save()
        self.assertEqual(user.get_start_ksg_display(), "V18")

    def test_get_start_ksg_display__user_in_autumn__returns_h_prefix_and_correct_year(self):
        user = UserFactory()
        user.start_ksg = timezone.datetime(year=2018, month=8, day=1)
        user.save()
        self.assertEqual(user.get_start_ksg_display(), "H18")

    def test_profile_image_url__no_image__returns_none(self):
        user = UserFactory(profile_image=None)
        self.assertEqual(user.profile_image_url, None)

    def test_profile_image_url__image_exists__returns_url(self):
        image_file = SimpleUploadedFile(name="test_image.jpeg", content=b'', content_type='image/jpeg')
        user = UserFactory(profile_image=image_file)
        self.assertIsNotNone(
            re.match(
                r'/media/profiles/test_image([_]\w*)?.jpeg',
                user.profile_image_url
            )
        )

    def test_active__status_is_active__returns_true(self):
        user = UserFactory(ksg_status=KSG_STATUS_TYPES.aktiv)
        self.assertEqual(user.active(), True)

    def test_active__status_is_not_active__returns_false(self):
        user = UserFactory(ksg_status=KSG_STATUS_TYPES.inaktiv)
        self.assertEqual(user.active(), False)
        user.ksg_status = KSG_STATUS_TYPES.permittert
        user.save()
        self.assertEqual(user.active(), False)
        user.ksg_status = KSG_STATUS_TYPES.sluttet
        user.save()
        self.assertEqual(user.active(), False)


class UserDetailViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username='username')
        cls.url = reverse('user_detail', kwargs={'user_id': cls.user.id})
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


# TODO test for changing info when not logged in and if changes are actually made
class UserFormTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user.set_password('password')
        cls.user.save()
        cls.user_detail_url = reverse(user_detail, kwargs={'user_id': cls.user.id})

    def test_UserForm_valid(self):
        form = UserForm(data={
            'first_name': "Alexander", 'last_name': "Orvik",
            'phone': "45087749", 'study': "Samf", 'biography': "Nå er det endret", 'email': "alexaor@stud.ntnu.no"})
        self.assertTrue(form.is_valid())

    def test_UserForm_invalid(self):
        form = UserForm(data={
            'first_name': "", 'last_name': "",
            'phone': "", 'study': "", 'email': ""})

        self.assertFalse(form.is_valid())

    def test_update_user_view_valid(self):
        self.client.login(username=self.user.email, password='password')
        response = self.client.post('/users/142/update', {
            'first_name': "Alexander", 'last_name': "Orvik",
            'phone': "45087749", 'study': "Samf", 'biography': "Nå er det endret", 'email': "alexaor@stud.ntnu.no"})
        self.assertEqual(response.status_code, 302)

    def test_update_user_get_request(self):
        self.client.login(username=self.user.username, password='password')
        response = self.client.get(reverse(update_user, kwargs={'user_id': self.user.id}))
        self.assertTemplateUsed(response, 'users/update_profile_page.html')

    def test_update_user_post_request_valid(self):
        self.client.login(username=self.user.username, password='password')
        response = self.client.post(reverse(update_user, kwargs={'user_id': self.user.id}), data={
            'first_name': "Alexander", 'last_name': "Orvik",
            'phone': "45087749", 'study': "Samf", 'biography': "Nå er det endret", 'email': "alexaor@stud.ntnu.no"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Alexander')
        self.assertEqual(self.user.last_name, 'Orvik')
        self.assertEqual(self.user.phone, '45087749')
        self.assertEqual(self.user.study, 'Samf')
        self.assertEqual(self.user.biography, 'Nå er det endret')
        self.assertEqual(self.user.email, 'alexaor@stud.ntnu.no')

    def test_update_user_post_request_invalid(self):
        self.client.login(username=self.user.username, password='password')
        response = self.client.post(reverse(update_user, kwargs={'user_id': self.user.id}), data={
            'first_name': "Alexander", 'last_name': "Orvik",
            'phone': "45087749", 'study': "Samf", 'biography': "Nå er det endret", 'email': ""})
        self.assertTemplateUsed(response, 'users/update_profile_page.html')

    def test_update_user_not_post_or_get_request(self):
        self.client.login(username=self.user.username, password='password')
        response = self.client.patch(reverse(update_user, kwargs={'user_id': self.user.id}))
        self.assertEqual(response.status_code, 405)

    # TODO add invalid view test and more comprehensive testing


class UsersHaveMadeOutModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user_two = UserFactory()
        cls.user_three = UserFactory()

    def test_str_and_repr__does_not_crash(self):
        made_out = UsersHaveMadeOutFactory(
            user_one=self.user,
            user_two=self.user_two
        )
        str(made_out)
        repr(made_out)


class UsersHaveMadeOutManagerTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.user_two = UserFactory()
        cls.user_three = UserFactory()
        cls.made_out_this_semester = UsersHaveMadeOutFactory(
            user_one=cls.user,
            user_two=cls.user_two,
        )
        now = timezone.now()
        cls.made_out_in_spring_last_year = UsersHaveMadeOutFactory(
            user_one=cls.user,
            user_two=cls.user_two,
            created=now.replace(year=now.year - 1, month=3, day=1)
        )
        cls.made_out_in_autumn_last_year = UsersHaveMadeOutFactory(
            user_one=cls.user,
            user_two=cls.user_two,
            created=now.replace(year=now.year - 1, month=9, day=1)
        )

    def test_this_semester__returns_made_outs_from_this_semester(self):
        this_semester_made_outs = UsersHaveMadeOut.objects.this_semester()
        self.assertEqual(this_semester_made_outs.count(), 1)
        self.assertEqual(this_semester_made_outs.first(), self.made_out_this_semester)

    def test_in_semester__this_semester_as_input__returns_made_outs_from_this_semester(self):
        made_outs = UsersHaveMadeOut.objects.in_semester(self.made_out_this_semester.created)
        self.assertEqual(made_outs.count(), 1)
        self.assertEqual(made_outs.first(), self.made_out_this_semester)

    def test_in_semester__specific_semester_in_spring_as_input__only_returns_relevant_made_outs(self):
        made_outs = UsersHaveMadeOut.objects.in_semester(self.made_out_in_spring_last_year.created)
        self.assertEqual(made_outs.count(), 1)
        self.assertEqual(made_outs.first(), self.made_out_in_spring_last_year)

    def test_in_semester__specific_semester_in_autumn_as_input__only_returns_relevant_made_outs(self):
        made_outs = UsersHaveMadeOut.objects.in_semester(self.made_out_in_autumn_last_year.created)
        self.assertEqual(made_outs.count(), 1)
        self.assertEqual(made_outs.first(), self.made_out_in_autumn_last_year)


class KlineKartViewTest(TestCase):

    @classmethod
    def tearDownClass(cls):
        super(KlineKartViewTest, cls).tearDownClass()
        # Delete the temporary media root
        shutil.rmtree(cls.temp_media_root)
        # Restore
        settings.MEDIA_ROOT = "/media/"

    @classmethod
    def setUpTestData(cls):
        # Set up mocking of the media root temporarily so we can create uploads
        cls.temp_media_root = tempfile.mkdtemp()
        settings.MEDIA_ROOT = cls.temp_media_root

        cls.user = UserFactory(anonymize_in_made_out_map=False)
        cls.user.set_password('password')
        cls.user.save()

        cls.user_two = UserFactory(anonymize_in_made_out_map=False)
        cls.user_three = UserFactory(anonymize_in_made_out_map=True)
        cls.user_four = UserFactory(anonymize_in_made_out_map=True)

    def setUp(self):
        self.client.login(
            username=self.user.username,
            password='password'
        )

    def test_klinekart__renders_the_klinekart_template(self):
        response = self.client.get(reverse(klinekart))
        self.assertTemplateUsed(response, 'users/klinekart.html')

    def test_klinekart__with_associations__sends_all_associations_properly_as_json(self):
        UsersHaveMadeOutFactory(
            user_one=self.user,
            user_two=self.user_two,
        )
        UsersHaveMadeOutFactory(
            user_one=self.user_two,
            user_two=self.user_three,
        )
        UsersHaveMadeOutFactory(
            user_one=self.user_three,
            user_two=self.user,
        )
        UsersHaveMadeOutFactory(
            user_one=self.user_four,
            user_two=self.user_two,
        )
        UsersHaveMadeOutFactory(
            user_one=self.user_four,
            user_two=self.user_three,
        )
        # Duplicates are allowed
        UsersHaveMadeOutFactory(
            user_one=self.user_two,
            user_two=self.user,
        )

        response: HttpResponse = self.client.get(reverse(klinekart))
        self.assertTemplateUsed(response, 'users/klinekart.html')

        data = json.loads(response.context['made_out_data'])
        self.assertEqual(len(data), 6)

        ids = set()
        names = set()
        imgs = set()

        for tuple in data:
            ids.add(tuple[0]['id'])
            ids.add(tuple[1]['id'])

            names.add(tuple[0]['name'])
            names.add(tuple[1]['name'])

            imgs.add(tuple[0]['img'])
            imgs.add(tuple[1]['img'])

        self.assertTrue(ids == {1, 2, -1, -2})
        self.assertTrue(names == {
            self.user.get_full_name(),
            self.user_two.get_full_name(),
            "Anonymous"
        })
        self.assertTrue(imgs == {
            self.user.profile_image_url,
            self.user_two.profile_image_url,
            None
        })
