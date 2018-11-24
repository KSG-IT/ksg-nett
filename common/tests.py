from django.template import Template, Context
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from common.util import get_semester_year_shorthand
from common.views import index
from users.models import User
from internal.views import index as internal_index
from login.views import login_user


class TestIndexView(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User(
            username='username',
            email='user@example.com'
        )
        cls.user.set_password('password')
        cls.user.save()

    def test_user_logged_in_redirects_to_internal(self):
        self.client.login(username='username', password='password')
        response = self.client.get(reverse(index))
        self.assertEqual(response.status_code, 302)
        self.assertIn('Location', response)
        self.assertEqual(response['Location'], reverse(internal_index))

    def test_user_not_logged_in_redirects_to_login(self):
        response = self.client.get(reverse(index))
        self.assertEqual(response.status_code, 302)
        self.assertIn('Location', response)
        self.assertEqual(response['Location'], reverse(login_user))

class TestGetSemesterYearShortHand(TestCase):
    def test_get_semester_year_shorthand__timestamp_in_spring__returns_v_prefix_and_correct_year(self):
        timestamp = timezone.datetime(year=2018, month=3, day=1)
        self.assertEqual(get_semester_year_shorthand(timestamp), "V18")

    def test_get_semester_year_shorthand__timestamp_in_autumn__returns_h_prefix_and_correct_year(self):
        timestamp = timezone.datetime(year=2018, month=8, day=1)
        self.assertEqual(get_semester_year_shorthand(timestamp), "H18")


class TestGetSemesterYearShortHandFilter(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.template = Template("""
            {% load ksg_helpers %} 
            {{ timestamp | get_semester_year_shorthand }}
        """)

    def test_get_semester_year_shorthand_filter__timestamp_in_spring__returns_v_prefix_and_correct_year(self):
        timestamp = timezone.datetime(year=2018, month=3, day=1)
        context = Context({'timestamp': timestamp})
        output = self.template.render(context)
        self.assertEqual(output.strip(), "V18")


    def test_get_semester_year_shorthand_filter__timestamp_in_autumn__returns_h_prefix_and_correct_year(self):
        timestamp = timezone.datetime(year=2018, month=8, day=1)
        context = Context({'timestamp': timestamp})
        output = self.template.render(context)
        self.assertEqual(output.strip(), "H18")

    def test_get_semester_year_shorthand_filter__bad_input_type__throws(self):
        with self.assertRaises(ValueError):
            context = Context({'timestamp': 25})
            output = self.template.render(context)

        with self.assertRaises(ValueError):
            # Sorry, strings doesn't work either
            context = Context({'timestamp': "2018-01-01T22:22:22Z"})
            output = self.template.render(context)

        with self.assertRaises(ValueError):
            context = Context({'timestamp': []})
            output = self.template.render(context)

