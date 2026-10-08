from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from admissions.consts import ApplicantStatus
from admissions.models import Admission, Applicant
from organization.tests.factories import InternalGroupPositionFactory
from users.tests.factories import UserFactory


def run(*args):
    call_command("generate_active_admission", *args, stdout=StringIO())


class TestGenerateActiveAdmission(TestCase):
    def setUp(self):
        UserFactory.create_batch(5)
        InternalGroupPositionFactory.create_batch(4, available_externally=True)

    def test__generated_data__is_consistent_with_applicant_status(self):
        run("--applicants", "120", "--seed", "1")
        now = timezone.now()
        applicants = Applicant.objects.all()

        self.assertEqual(applicants.count(), 120)
        self.assertEqual(Admission.objects.count(), 1)
        for status in ApplicantStatus.values:
            self.assertTrue(
                applicants.filter(status=status).exists(), f"No applicants in {status}"
            )
        self.assertFalse(applicants.filter(token__isnull=True).exists())

        email_sent = applicants.filter(status=ApplicantStatus.EMAIL_SENT)
        self.assertFalse(email_sent.exclude(first_name=None).exists())
        self.assertFalse(email_sent.filter(priorities__isnull=False).exists())

        registered = applicants.filter(status=ApplicantStatus.HAS_REGISTERED_PROFILE)
        self.assertFalse(registered.filter(first_name=None).exists())
        self.assertFalse(registered.filter(priorities__isnull=False).exists())

        set_priorities = applicants.filter(status=ApplicantStatus.HAS_SET_PRIORITIES)
        self.assertFalse(set_priorities.filter(priorities__isnull=True).exists())
        self.assertFalse(set_priorities.filter(interview__isnull=False).exists())

        scheduled = applicants.filter(status=ApplicantStatus.SCHEDULED_INTERVIEW)
        self.assertFalse(scheduled.filter(interview__isnull=True).exists())
        self.assertFalse(scheduled.filter(interview__interview_start__lt=now).exists())

        for status in [
            ApplicantStatus.INTERVIEW_FINISHED,
            ApplicantStatus.DID_NOT_SHOW_UP_FOR_INTERVIEW,
        ]:
            past = applicants.filter(status=status)
            self.assertFalse(past.filter(interview__isnull=True).exists())
            self.assertFalse(past.filter(interview__interview_end__gt=now).exists())

        finished = applicants.filter(status=ApplicantStatus.INTERVIEW_FINISHED)
        self.assertTrue(finished.filter(open_for_other_positions=True).exists())
        self.assertTrue(finished.filter(open_for_other_positions=False).exists())
        self.assertFalse(
            applicants.exclude(status=ApplicantStatus.INTERVIEW_FINISHED)
            .filter(open_for_other_positions=True)
            .exists()
        )
        self.assertFalse(finished.filter(interview__total_evaluation=None).exists())
        self.assertFalse(finished.filter(interview__interviewers=None).exists())
        self.assertFalse(
            finished.filter(
                interview__boolean_evaluation_answers__value__isnull=True
            ).exists()
        )

    def test__more_applicants_than_interviews__keeps_data_consistent(self):
        run("--applicants", "300", "--locations", "1")
        scheduled_without_interview = Applicant.objects.filter(
            status__in=[
                ApplicantStatus.SCHEDULED_INTERVIEW,
                ApplicantStatus.INTERVIEW_FINISHED,
            ],
            interview__isnull=True,
        )
        self.assertFalse(scheduled_without_interview.exists())

    def test__existing_active_admission__requires_reset(self):
        run("--applicants", "10")
        with self.assertRaises(CommandError):
            run("--applicants", "10")

        run("--applicants", "10", "--reset")
        self.assertEqual(Admission.objects.count(), 1)
        self.assertEqual(Applicant.objects.count(), 10)

    def test__reset__keeps_closed_admissions(self):
        from admissions.consts import AdmissionStatus
        from admissions.models import Interview, InterviewLocation

        closed = Admission.objects.create(status=AdmissionStatus.CLOSED)
        location = InterviewLocation.objects.create(name="Gammelt rom")
        # Inside the new interview period, to check it is not cleared
        start = timezone.now() - timezone.timedelta(days=1)
        old_interview = Interview.objects.create(
            location=location,
            interview_start=start,
            interview_end=start + timezone.timedelta(minutes=30),
        )
        old_applicant = Applicant.objects.create(
            admission=closed, email="old@example.com", interview=old_interview
        )

        run("--applicants", "20")
        run("--applicants", "20", "--reset")

        self.assertTrue(Admission.objects.filter(id=closed.id).exists())
        self.assertTrue(Applicant.objects.filter(id=old_applicant.id).exists())
        self.assertTrue(Interview.objects.filter(id=old_interview.id).exists())
        self.assertEqual(
            Admission.objects.exclude(status=AdmissionStatus.CLOSED).count(), 1
        )
        self.assertEqual(Applicant.objects.exclude(admission=closed).count(), 20)

    def test__missing_positions__raises_command_error(self):
        from organization.models import InternalGroupPosition

        InternalGroupPosition.objects.update(available_externally=False)
        with self.assertRaises(CommandError):
            run("--applicants", "10")
