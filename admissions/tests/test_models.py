from django.test import TestCase

from admissions.utils import (
    get_available_interview_locations,
    generate_interviews_from_schedule,
)
from admissions.models import (
    Interview,
    InterviewLocation,
    InterviewScheduleTemplate,
    InterviewLocationAvailability,
)
from datetime import datetime, timedelta


class TestInterviewModel(TestCase):
    def setUp(self) -> None:
        # We set up 3 locations for interviews
        now = datetime.now()
        self.interview_start = datetime(
            now.year, now.month, now.day, hour=12, minute=0, second=0
        )
        self.interview_location = InterviewLocation.objects.create(name="Knaus")
        Interview.objects.create(
            location=self.interview_location,
            interview_start=self.interview_start,
            interview_end=self.interview_start + timedelta(minutes=30),
        )

    def test__overlapping_interview__does_not_create_interview_instances(self):
        interview_early_start = self.interview_start + timedelta(minutes=15)
        interview_late_end = interview_early_start - timedelta(minutes=30)
        interview_count = Interview.objects.all().count()
        Interview.objects.create(
            location=self.interview_location,
            interview_start=interview_early_start,
            interview_end=interview_early_start + timedelta(minutes=30),
        )

        Interview.objects.create(
            location=self.interview_location,
            interview_start=interview_late_end,
            interview_end=interview_late_end + timedelta(minutes=30),
        )
        self.assertEqual(Interview.objects.all().count(), interview_count)
