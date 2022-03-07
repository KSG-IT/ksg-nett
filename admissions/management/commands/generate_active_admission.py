from django.core.management.base import BaseCommand, CommandError
from admissions.models import (
    Admission,
    Applicant,
    InterviewScheduleTemplate,
    Interview,
    InterviewLocation,
    InterviewLocationAvailability,
    AdmissionAvailableInternalGroupPositionData,
    InterviewBooleanEvaluation,
    InterviewBooleanEvaluationAnswer,
    InterviewAdditionalEvaluationAnswer,
    InterviewAdditionalEvaluationStatement,
)
from admissions.tests.factories import ApplicantFactory
from admissions.consts import AdmissionStatus, ApplicantStatus
from organization.models import InternalGroupPosition
from admissions.utils import generate_interviews_from_schedule
import datetime
from common.util import date_time_combiner
from common.management.commands._utils import (
    chose_random_element,
    get_random_model_objects,
)
from admissions.management.commands._consts import (
    INTERVIEW_NOTES_TEXT,
    INTERVIEW_DISCUSSION_TEXT,
)
from users.models import User


class Command(BaseCommand):
    """
    Algorithm:
        1. Generate default interview schedule template if it does not exist
            - Should create an interview period which started a week ago and has another week left
        2. Generate interviews
        3. Generate available positions
        4. Randomize applicants
            - Their state in the interview process
            - Their priorities
        5. Randomize interviews
            - Content
            - Interviewers
    """

    def handle(self, *args, **options):
        try:
            self.generate_interview_schedule()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"{e}"))
            raise CommandError(e)
        self.stdout.write(self.style.SUCCESS("Active admission has been generated"))

    def generate_interview_schedule(self):
        """"""
        now = datetime.date.today()
        last_week = now - datetime.timedelta(days=7)
        next_week = now + datetime.timedelta(days=7)
        day_start = datetime.time(hour=12, minute=0, second=0)
        day_end = datetime.time(hour=20, minute=0, second=0)
        interview_duration = datetime.timedelta(hours=0, minutes=30, seconds=0)
        pause_duration = datetime.timedelta(hours=1, minutes=0, seconds=0)
        block_size = 5
        self.stdout.write(
            self.style.SUCCESS(
                f"Creating interview schedule from {last_week} to {next_week} with these settings:"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"""
            > Interview start for each day is {day_start}
            > Maximum interview end for each day is {day_end}
            > Default interviews in a row before a break is {block_size}
            > Default interview duration is {interview_duration}
            > Default pause duration is {pause_duration}
        """
            )
        )

        # We design around the model only ever having one instance
        # An idea could be to have a OneToONe rel with admission and then always try to copy the defaults from 1 year ago
        schedule = InterviewScheduleTemplate.get_or_create_interview_schedule_template()
        schedule.interview_period_start_date = last_week
        schedule.interview_period_end_date = next_week
        schedule.default_interview_day_start = day_start
        schedule.default_interview_day_end = day_end
        schedule.default_interview_duration = interview_duration
        schedule.default_pause_duration = pause_duration
        schedule.default_block_size = block_size
        schedule.save()

        # Create two interview locations

        locations = [
            InterviewLocation.objects.get_or_create(name="Bodegaen")[0],
            InterviewLocation.objects.get_or_create(name="Knaus")[0],
        ]
        self.stdout.write(self.style.SUCCESS(f"Created {len(locations)} locations"))
        # Make the locations available 12:00 to 20:00 each day in the interview period
        self.stdout.write(
            self.style.SUCCESS(
                f"Making locations available from {day_start} to {day_end} for each day in the interview period"
            )
        )
        cursor = last_week
        while cursor <= next_week:
            for location in locations:
                datetime_from = date_time_combiner(cursor, day_start)
                datetime_to = date_time_combiner(cursor, day_end)
                InterviewLocationAvailability.objects.create(
                    interview_location=location,
                    datetime_from=datetime_from,
                    datetime_to=datetime_to,
                )
            cursor += datetime.timedelta(days=1)

        self.stdout.write(
            self.style.SUCCESS(f"Retrieving or creating admission object")
        )
        # Get or an admission
        admission = Admission.objects.get_or_create(
            status=AdmissionStatus.OPEN, date=last_week - datetime.timedelta(days=3)
        )[0]

        # Add some ordinarily available positions
        self.stdout.write(self.style.SUCCESS("Creating available positions"))
        positions = InternalGroupPosition.objects.all().filter(
            available_externally=True
        )
        available_position_choices = [5, 10, 15]
        for position in positions:
            number = chose_random_element(available_position_choices)
            AdmissionAvailableInternalGroupPositionData.objects.create(
                admission=admission,
                internal_group_position=position,
                available_positions=number,
            )
            self.stdout.write(
                self.style.SUCCESS(f"Created {position.name} with {number} spots")
            )

        # Interview generation
        generate_interviews_from_schedule(schedule)
        interview_period_datetime_start = date_time_combiner(last_week, day_start)
        number_of_interviews = Interview.objects.filter(
            interview_start__gte=interview_period_datetime_start
        ).count()
        self.stdout.write(
            self.style.SUCCESS(f"Generated {number_of_interviews} interviews")
        )

        # Applicant generation distributed randomly across the admission
        self.stdout.write(self.style.SUCCESS("Creating 200 applicants "))
        ApplicantFactory.create_batch(200, admission=admission)

        # Applicants now need to be filtered by status and their data parsed.
        # Example being purging data for those who just got an email or assigning them to interviews
        self.stdout.write(
            self.style.SUCCESS("Grouping applicants together based on status")
        )
        email_sent_applicants = Applicant.objects.all().filter(
            status=ApplicantStatus.EMAIL_SENT
        )
        registered_profile__applicants = Applicant.objects.all().filter(
            status=ApplicantStatus.HAS_REGISTERED_PROFILE
        )
        interview_scheduled_applicants = Applicant.objects.all().filter(
            status=ApplicantStatus.SCHEDULED_INTERVIEW
        )
        finished_with_interview_applicants = Applicant.objects.all().filter(
            status=ApplicantStatus.INTERVIEW_FINISHED
        )
        ghosted_applicants = Applicant.objects.all().filter(
            status=ApplicantStatus.DID_NOT_SHOW_UP_FOR_INTERVIEW
        )
        retracted_applicants = Applicant.objects.all().filter(
            status=ApplicantStatus.RETRACTED_APPLICATION
        )

        # Nuke details
        count = email_sent_applicants.update(
            first_name="",
            last_name="",
            date_of_birth=None,
            phone="",
            hometown="",
            address="",
        )
        self.stdout.write(
            self.style.SUCCESS(f"Reset personal details for {count} applicants")
        )

        # We assign each applicant to a random interview in the future
        datetime_today = date_time_combiner(now, day_start)
        self.stdout.write(
            self.style.SUCCESS(
                f"Assigning random future interviews to {interview_scheduled_applicants.count()} applicants"
            )
        )
        for applicant in interview_scheduled_applicants:
            random_interview = (
                Interview.objects.all()
                .filter(applicant__isnull=True, interview_start__lte=datetime_today)
                .order_by("?")
                .first()
            )
            applicant.interview = random_interview
            applicant.save()

        self.stdout.write(
            self.style.SUCCESS("Adding random interviewers to interviews")
        )
        number_of_interviewers_choices = [3, 4, 5]
        for applicant in finished_with_interview_applicants:
            self.stdout.write(
                self.style.SUCCESS(f"Generating interview data for {applicant}")
            )
            random_interview = (
                Interview.objects.all()
                .filter(applicant__isnull=True, interview_start__gte=datetime_today)
                .order_by("?")
                .first()
            )
            applicant.interview = random_interview
            applicant.save()
            number_of_interviewers = chose_random_element(
                number_of_interviewers_choices
            )
            random_interviewers = get_random_model_objects(User, number_of_interviewers)
            random_interview.interviewers.set(random_interviewers)
            random_interview.discussion = INTERVIEW_DISCUSSION_TEXT
            random_interview.notes = INTERVIEW_NOTES_TEXT

            boolean_evaluations = InterviewBooleanEvaluation.objects.all()
            additional_evaluations = (
                InterviewAdditionalEvaluationStatement.objects.all()
            )

            for statement in boolean_evaluations:
                random_answer = chose_random_element([True, False])
                InterviewBooleanEvaluationAnswer.objects.create(
                    interview=random_interview, statement=statement, value=random_answer
                )
            additional_evaluation_answer_choices = (
                InterviewAdditionalEvaluationAnswer.Options.values
            )
            for statement in additional_evaluations:
                random_answer = chose_random_element(
                    additional_evaluation_answer_choices
                )
                InterviewAdditionalEvaluationAnswer.objects.create(
                    interview=random_interview,
                    statement=statement,
                    answer=random_answer,
                )
            applicant.save()
            random_interview.save()

        self.stdout.write(self.style.SUCCESS("Giving all applicants random priorities"))
        # Now we give the applicants random priorities
        number_of_priorities_choices = [2, 3]
        for applicant in Applicant.objects.all():
            number_of_priorities = chose_random_element(number_of_priorities_choices)
            positions = (
                InternalGroupPosition.objects.all()
                .filter(available_externally=True)
                .order_by("?")[0:number_of_priorities]
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Adding positions {positions} to {applicant} priorities"
                )
            )
            for position in positions:
                applicant.add_priority(position)
