from datetime import datetime
from unittest.mock import patch

from django.template import Template, Context
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from common.util import get_semester_year_shorthand, get_semester_year_shorthands_by_count, \
    get_semester_year_shorthands_by_date, get_semester_date_boundaries_from_shorthand, is_valid_semester_year_shorthand
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


class TestGetSemesterYearShorthandsByDate(TestCase):
    def test_get_semester_year_shorthands_by_date__argument_is_in_this_semester__returns_array_with_this_semester_only(self):
        # Patch timezone now, so we can make reliable tests without re-implementing the
        # method itself in the test
        with patch(
                'django.utils.timezone.now',
                return_value=datetime(2018, 1, 1, tzinfo=timezone.utc)
        ):
            date = timezone.datetime(2018, 1, 1, tzinfo=timezone.utc)
            results = get_semester_year_shorthands_by_date(date)
            self.assertListEqual(
                results,
                ["V18"]
            )

    def test_get_semester_year_shorthands_by_date__argument_is_5_semesters_back__returns_correct_result(self):
        with patch(
                'django.utils.timezone.now',
                return_value=datetime(2018, 1, 1, tzinfo=timezone.utc)
        ):
            date = timezone.datetime(2016, 1, 1, tzinfo=timezone.utc)
            results = get_semester_year_shorthands_by_date(date)
            self.assertListEqual(
                results,
                ["V18", "H17", "V17", "H16", "V16"]
            )

    def test_get_semester_year_shorthands_by_date__argument_is_in_the_future__returns_empty_list(self):
        with patch(
                'django.utils.timezone.now',
                return_value=datetime(2018, 1, 1, tzinfo=timezone.utc)
        ):
            date = timezone.datetime(2019, 1, 1, tzinfo=timezone.utc)
            results = get_semester_year_shorthands_by_date(date)
            self.assertListEqual(
                results,
                []
            )

    def test_get_semester_year_shorthands_by_date__argument_is_around_century_change__returns_correct_result(self):
        with patch(
                'django.utils.timezone.now',
                return_value=datetime(2001, 1, 1, tzinfo=timezone.utc)
        ):
            date = timezone.datetime(1999, 1, 1, tzinfo=timezone.utc)
            results = get_semester_year_shorthands_by_date(date)
            self.assertListEqual(
                results,
                ["V01", "H00", "V00", "H99", "V99"]
            )


class TestGetSemesterYearShorthandsByCount(TestCase):

    def test_get_semester_year_shorthands_by_count__argument_is_one__returns_correct_result(self):
        # Patch timezone now, so we can make reliable tests without re-implementing the
        # method itself in the test
        with patch(
                'django.utils.timezone.now',
                return_value=datetime(2018, 1, 1, tzinfo=timezone.utc)
        ):
            results = get_semester_year_shorthands_by_count(1)
            self.assertListEqual(
                results,
                ["V18"]
            )

    def test_get_semester_year_shorthands_by_count__regular_positive_integer__returns_correct_result(self):
        with patch(
            'django.utils.timezone.now',
            return_value=datetime(2018, 1, 1, tzinfo=timezone.utc)
        ):
            results = get_semester_year_shorthands_by_count(5)
            self.assertListEqual(
                results,
                ["V18", "H17", "V17", "H16", "V16"]
            )

    def test_get_semester_year_shorthands_by_count__negative_integer__returns_empty_list(self):
        results = get_semester_year_shorthands_by_count(-1)
        self.assertListEqual(results, [])

    def test_get_semester_year_shorthands_by_count__timezone_now_around_century_change__returns_correct_result(self):
        # This test simultaneously tests that we can render numbers 0-9 with leading zeros
        # and that we handle the century change.

        with patch(
                'django.utils.timezone.now',
                return_value=datetime(2001, 1, 1, tzinfo=timezone.utc)
        ):
            results = get_semester_year_shorthands_by_count(5)
            self.assertListEqual(
                results,
                ["V01", "H00", "V00", "H99", "V99"]
            )



class TestGetSemesterDateBoundariesFromShorthand(TestCase):
    def test_get_semester_date_boundaries_from_shorthand__input_in_spring_and_2000s__returns_correct_result(self):
        start, end = get_semester_date_boundaries_from_shorthand("V18")
        expected_tzinfo = timezone.now().tzinfo
        self.assertEqual(
            start,
            timezone.datetime(
                2018,
                1,
                1,
                tzinfo=expected_tzinfo
            )
        )
        self.assertEqual(
            end,
            timezone.datetime(
                2018,
                7,
                1,
                tzinfo=expected_tzinfo
            )
        )

    def test_get_semester_date_boundaries_from_shorthand__input_in_autumn_and_2000s__returns_correct_result(self):
        start, end = get_semester_date_boundaries_from_shorthand("H18")
        expected_tzinfo = timezone.now().tzinfo
        self.assertEqual(
            start,
            timezone.datetime(
                2018,
                7,
                1,
                tzinfo=expected_tzinfo
            )
        )
        self.assertEqual(
            end,
            timezone.datetime(
                2019,
                1,
                1,
                tzinfo=expected_tzinfo
            )
        )

    def test_get_semester_date_boundaries_from_shorthand__input_in_spring_and_1900s__returns_correct_result(self):
        start, end = get_semester_date_boundaries_from_shorthand("V99")
        expected_tzinfo = timezone.now().tzinfo
        self.assertEqual(
            start,
            timezone.datetime(
                1999,
                1,
                1,
                tzinfo=expected_tzinfo
            )
        )
        self.assertEqual(
            end,
            timezone.datetime(
                1999,
                7,
                1,
                tzinfo=expected_tzinfo
            )
        )

    def test_get_semester_date_boundaries_from_shorthand__input_in_autumn_and_1900s__returns_correct_result(self):
        start, end = get_semester_date_boundaries_from_shorthand("H99")
        expected_tzinfo = timezone.now().tzinfo
        self.assertEqual(
            start,
            timezone.datetime(
                1999,
                7,
                1,
                tzinfo=expected_tzinfo
            )
        )
        self.assertEqual(
            end,
            timezone.datetime(
                2000,
                1,
                1,
                tzinfo=expected_tzinfo
            )
        )

    def test_get_semester_date_boundaries_from_shorthand__invalid_input__raises_valueerror(self):
        with self.assertRaises(ValueError):
            get_semester_date_boundaries_from_shorthand("Kebab")

        with self.assertRaises(ValueError):
            get_semester_date_boundaries_from_shorthand("H0")

        with self.assertRaises(ValueError):
            get_semester_date_boundaries_from_shorthand("H1999")


class TestIsValidSemesterYearShorthand(TestCase):
    def test_is_valid_semester_year_shorthand__valid_spring_input__returns_true(self):
        self.assertTrue(is_valid_semester_year_shorthand("V18"))
        self.assertTrue(is_valid_semester_year_shorthand("V99"))
        self.assertTrue(is_valid_semester_year_shorthand("V05"))
        self.assertTrue(is_valid_semester_year_shorthand("V00"))

    def test_is_valid_semester_year_shorthand__valid_autumn_input__returns_true(self):
        self.assertTrue(is_valid_semester_year_shorthand("H18"))
        self.assertTrue(is_valid_semester_year_shorthand("H99"))
        self.assertTrue(is_valid_semester_year_shorthand("H05"))
        self.assertTrue(is_valid_semester_year_shorthand("H00"))

    def test_is_valid_semester_year_shorthand__invalid_input__returns_false(self):
        self.assertFalse(is_valid_semester_year_shorthand("H0"))
        self.assertFalse(is_valid_semester_year_shorthand("V0"))
        self.assertFalse(is_valid_semester_year_shorthand("H013"))
        self.assertFalse(is_valid_semester_year_shorthand("V013"))
        self.assertFalse(is_valid_semester_year_shorthand("H1999"))
        self.assertFalse(is_valid_semester_year_shorthand("V1999"))
        self.assertFalse(is_valid_semester_year_shorthand("HV199"))
        self.assertFalse(is_valid_semester_year_shorthand("VV199"))
        self.assertFalse(is_valid_semester_year_shorthand("Kebab"))
        self.assertFalse(is_valid_semester_year_shorthand("A18"))
