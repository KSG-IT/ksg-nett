import datetime
import math
import random
from secrets import token_urlsafe

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from faker import Faker

from admissions.consts import (
    AdmissionStatus,
    ApplicantStatus,
    InternalGroupStatus,
    Priority,
)
from admissions.management.commands._consts import (
    INTERVIEW_DISCUSSION_TEXT,
    INTERVIEW_NOTES_TEXT,
)
from admissions.models import (
    Admission,
    AdmissionAvailableInternalGroupPositionData,
    Applicant,
    ApplicantComment,
    ApplicantInterest,
    ApplicantRecommendation,
    InternalGroupPositionPriority,
    Interview,
    InterviewAdditionalEvaluationAnswer,
    InterviewAdditionalEvaluationStatement,
    InterviewBooleanEvaluation,
    InterviewBooleanEvaluationAnswer,
    InterviewLocation,
    InterviewLocationAvailability,
    InterviewScheduleTemplate,
)
from admissions.utils import generate_interviews_from_schedule
from common.util import date_time_combiner
from organization.models import InternalGroupPosition
from users.models import User

# Share of applicants in each status. Finished gets the remainder.
STATUS_DISTRIBUTION = [
    (ApplicantStatus.EMAIL_SENT, 0.10),
    (ApplicantStatus.HAS_REGISTERED_PROFILE, 0.10),
    (ApplicantStatus.HAS_SET_PRIORITIES, 0.10),
    (ApplicantStatus.SCHEDULED_INTERVIEW, 0.25),
    (ApplicantStatus.DID_NOT_SHOW_UP_FOR_INTERVIEW, 0.07),
    (ApplicantStatus.RETRACTED_APPLICATION, 0.08),
    (ApplicantStatus.INTERVIEW_FINISHED, None),
]

HAS_PRIORITIES = [
    ApplicantStatus.HAS_SET_PRIORITIES,
    ApplicantStatus.SCHEDULED_INTERVIEW,
    ApplicantStatus.INTERVIEW_FINISHED,
    ApplicantStatus.DID_NOT_SHOW_UP_FOR_INTERVIEW,
    ApplicantStatus.RETRACTED_APPLICATION,
]
HAS_PERSONAL_DETAILS = [ApplicantStatus.HAS_REGISTERED_PROFILE] + HAS_PRIORITIES
NEEDS_FUTURE_INTERVIEW = [ApplicantStatus.SCHEDULED_INTERVIEW]
NEEDS_PAST_INTERVIEW = [
    ApplicantStatus.INTERVIEW_FINISHED,
    ApplicantStatus.DID_NOT_SHOW_UP_FOR_INTERVIEW,
]

DEFAULT_BOOLEAN_STATEMENTS = [
    "Kan jobbe nattevakter",
    "Har erfaring fra servering",
    "Kan jobbe i eksamensperioden",
]
DEFAULT_ADDITIONAL_STATEMENTS = [
    "Er energisk",
    "Er en lagspiller",
    "Er strukturert",
]
LOCATION_NAMES = ["Bodegaen", "Knaus", "Biblioteket"]

INTERVIEW_DAYS_BEFORE_TODAY = 7
INTERVIEW_DAYS_AFTER_TODAY = 7
DAY_START = datetime.time(hour=12)
DAY_END = datetime.time(hour=20)
INTERVIEW_DURATION = datetime.timedelta(minutes=30)
PAUSE_DURATION = datetime.timedelta(hours=1)
BLOCK_SIZE = 5


class Command(BaseCommand):
    help = (
        "Generates an active admission with interviews and applicants in every "
        "status. Use --applicants to stress test the admission views."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--applicants",
            type=int,
            default=200,
            help="Number of applicants to generate (default 200)",
        )
        parser.add_argument(
            "--locations",
            type=int,
            default=None,
            help="Number of interview locations. Default: enough for all applicants",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete admissions that are not closed, with their applicants and "
                "booked interviews. Closed admissions are kept."
            ),
        )
        parser.add_argument(
            "--seed", type=int, default=None, help="Seed for repeatable data"
        )

    def handle(self, *args, **options):
        number_of_applicants = options["applicants"]
        if number_of_applicants < 1:
            raise CommandError("--applicants must be at least 1")

        if options["seed"] is not None:
            random.seed(options["seed"])
            Faker.seed(options["seed"])
        self.fake = Faker("no_NO")

        if Admission.get_active_admission() and not options["reset"]:
            raise CommandError(
                "An active admission already exists. Run with --reset to replace it."
            )

        self.positions = list(
            InternalGroupPosition.objects.filter(
                available_externally=True
            ).select_related("internal_group")
        )
        if not self.positions:
            raise CommandError(
                "No internal group positions are available externally. "
                "Run generate_testdata first or mark positions as available_externally."
            )
        self.users = list(User.objects.all()[:200])
        if len(self.users) < 3:
            raise CommandError(
                "At least 3 users are needed as interviewers. Run generate_testdata first."
            )

        with transaction.atomic():
            if options["reset"]:
                self.delete_active_admissions()
            self.generate(number_of_applicants, options["locations"])

        self.stdout.write(self.style.SUCCESS("Active admission has been generated"))

    def delete_active_admissions(self):
        """
        Delete admissions that are not closed. Applicants and their related data
        cascade from the admission. Booked interviews do not, so delete them too.
        Do not delete interviews or locations of closed admissions: deleting an
        interview cascades to its applicant.
        """
        active = Admission.objects.exclude(status=AdmissionStatus.CLOSED)
        booked_interview_ids = list(
            Interview.objects.filter(applicant__admission__in=active).values_list(
                "id", flat=True
            )
        )
        admissions = active.count()
        applicants = Applicant.objects.filter(admission__in=active).count()
        active.delete()
        Interview.objects.filter(id__in=booked_interview_ids).delete()
        self.log(
            f"Deleted {admissions} non-closed admission(s), {applicants} applicants "
            f"and {len(booked_interview_ids)} booked interviews"
        )

    def clear_interview_period(self, schedule, locations):
        """Remove unbooked interviews and availability in the new period, so the
        generator does not create duplicates"""
        start = date_time_combiner(schedule.interview_period_start_date, datetime.time())
        end = date_time_combiner(
            schedule.interview_period_end_date, datetime.time(23, 59, 59)
        )
        unbooked, _ = Interview.objects.filter(
            applicant__isnull=True, interview_start__gte=start, interview_start__lte=end
        ).delete()
        InterviewLocationAvailability.objects.filter(
            interview_location__in=locations,
            datetime_from__lte=end,
            datetime_to__gte=start,
        ).delete()
        if unbooked:
            self.log(f"Deleted {unbooked} unbooked interviews in the interview period")

    def log(self, message):
        self.stdout.write(self.style.SUCCESS(message))

    def generate(self, number_of_applicants, number_of_locations):
        today = timezone.localdate()
        self.now = timezone.now()
        status_counts = self.get_status_counts(number_of_applicants)

        if number_of_locations is None:
            number_of_locations = self.get_needed_locations(status_counts)

        self.ensure_evaluation_statements()
        schedule = self.create_schedule(today)
        locations = self.get_locations(number_of_locations)
        self.clear_interview_period(schedule, locations)
        self.create_availability(locations, schedule)
        admission = self.create_admission(today)

        generate_interviews_from_schedule(schedule)
        self.log(
            f"Generated {Interview.objects.count()} interviews at {len(locations)} locations"
        )

        applicants = self.create_applicants(admission, status_counts)
        self.assign_interviews(applicants)
        self.create_priorities(applicants)
        self.fill_finished_interviews(applicants)
        self.create_applicant_activity(applicants)

        for status, _ in STATUS_DISTRIBUTION:
            count = sum(1 for a in applicants if a.status == status)
            self.log(f"  {status}: {count}")

    def get_status_counts(self, total):
        counts = {}
        for status, share in STATUS_DISTRIBUTION:
            if share is None:
                counts[status] = total - sum(counts.values())
            else:
                counts[status] = math.floor(total * share)
        return counts

    def get_needed_locations(self, status_counts):
        # Each location gets 2 * BLOCK_SIZE interviews per day. Today is left out to
        # keep a margin, since some of its interviews are past and some are future.
        per_location_past = 2 * BLOCK_SIZE * INTERVIEW_DAYS_BEFORE_TODAY
        per_location_future = 2 * BLOCK_SIZE * INTERVIEW_DAYS_AFTER_TODAY
        past_needed = sum(status_counts[s] for s in NEEDS_PAST_INTERVIEW)
        future_needed = sum(status_counts[s] for s in NEEDS_FUTURE_INTERVIEW)
        return max(
            2,
            math.ceil(past_needed / per_location_past),
            math.ceil(future_needed / per_location_future),
        )

    def ensure_evaluation_statements(self):
        if not InterviewBooleanEvaluation.objects.exists():
            for order, statement in enumerate(DEFAULT_BOOLEAN_STATEMENTS):
                InterviewBooleanEvaluation.objects.create(
                    statement=statement, order=order
                )
        if not InterviewAdditionalEvaluationStatement.objects.exists():
            for order, statement in enumerate(DEFAULT_ADDITIONAL_STATEMENTS):
                InterviewAdditionalEvaluationStatement.objects.create(
                    statement=statement, order=order
                )

    def create_schedule(self, today):
        start = today - datetime.timedelta(days=INTERVIEW_DAYS_BEFORE_TODAY)
        end = today + datetime.timedelta(days=INTERVIEW_DAYS_AFTER_TODAY)
        # The model only allows one instance
        schedule = InterviewScheduleTemplate.get_or_create_interview_schedule_template()
        schedule.interview_period_start_date = start
        schedule.interview_period_end_date = end
        schedule.default_interview_day_start = DAY_START
        schedule.default_interview_day_end = DAY_END
        schedule.default_interview_duration = INTERVIEW_DURATION
        schedule.default_pause_duration = PAUSE_DURATION
        schedule.default_block_size = BLOCK_SIZE
        schedule.save()
        self.log(f"Interview period {start} to {end}")
        return schedule

    def get_locations(self, number_of_locations):
        names = LOCATION_NAMES + [
            f"Rom {i}" for i in range(len(LOCATION_NAMES) + 1, number_of_locations + 1)
        ]
        return [
            InterviewLocation.objects.get_or_create(name=name)[0]
            for name in names[:number_of_locations]
        ]

    def create_availability(self, locations, schedule):
        availabilities = []
        cursor = schedule.interview_period_start_date
        while cursor <= schedule.interview_period_end_date:
            for location in locations:
                availabilities.append(
                    InterviewLocationAvailability(
                        interview_location=location,
                        datetime_from=date_time_combiner(cursor, DAY_START),
                        datetime_to=date_time_combiner(cursor, DAY_END),
                    )
                )
            cursor += datetime.timedelta(days=1)
        InterviewLocationAvailability.objects.bulk_create(availabilities)

    def create_admission(self, today):
        admission = Admission.objects.create(
            status=AdmissionStatus.OPEN,
            date=today - datetime.timedelta(days=INTERVIEW_DAYS_BEFORE_TODAY + 3),
        )
        AdmissionAvailableInternalGroupPositionData.objects.bulk_create(
            AdmissionAvailableInternalGroupPositionData(
                admission=admission,
                internal_group_position=position,
                available_positions=random.choice([5, 10, 15]),
            )
            for position in self.positions
        )
        self.log(
            f"Created admission {admission.semester} with {len(self.positions)} positions"
        )
        return admission

    def create_applicants(self, admission, status_counts):
        statuses = [
            status for status, count in status_counts.items() for _ in range(count)
        ]
        random.shuffle(statuses)
        applicants = []
        for index, status in enumerate(statuses):
            applicant = Applicant(
                admission=admission,
                email=f"applicant{index}.{token_urlsafe(4)}@example.com",
                token=token_urlsafe(32),
                status=status,
                last_activity=self.now
                - datetime.timedelta(minutes=random.randint(0, 60 * 24 * 14)),
            )
            if status in HAS_PERSONAL_DETAILS:
                applicant.first_name = self.fake.first_name()
                applicant.last_name = self.fake.last_name()
                applicant.phone = self.fake.phone_number()[:32]
                applicant.date_of_birth = self.fake.date_of_birth(
                    minimum_age=19, maximum_age=26
                )
                applicant.study = random.choice(
                    ["Datateknologi", "Industriell økonomi", "Psykologi", "Medisin"]
                )
                applicant.address = self.fake.street_address()[:100]
                applicant.hometown = self.fake.city()[:100]
                applicant.gdpr_consent = True
                applicant.wants_digital_interview = random.random() < 0.1
            applicants.append(applicant)

        applicants = Applicant.objects.bulk_create(applicants)
        self.log(f"Created {len(applicants)} applicants")
        return applicants

    def assign_interviews(self, applicants):
        free_interviews = Interview.objects.filter(applicant__isnull=True)
        past = list(free_interviews.filter(interview_end__lte=self.now))
        future = list(free_interviews.filter(interview_start__gte=self.now))
        random.shuffle(past)
        random.shuffle(future)

        for applicant in applicants:
            if applicant.status in NEEDS_PAST_INTERVIEW:
                pool = past
            elif applicant.status in NEEDS_FUTURE_INTERVIEW:
                pool = future
            else:
                continue

            if pool:
                applicant.interview = pool.pop()
            else:
                # Not enough interviews: keep the data consistent instead of failing
                applicant.status = ApplicantStatus.HAS_SET_PRIORITIES

        Applicant.objects.bulk_update(applicants, ["interview", "status"])
        self.log(
            f"Assigned {sum(1 for a in applicants if a.interview_id)} interviews"
        )

    def create_priorities(self, applicants):
        priorities = []
        for applicant in applicants:
            if applicant.status not in HAS_PRIORITIES:
                continue
            number_of_priorities = min(
                random.choice([1, 2, 3, 3, 3]), len(self.positions)
            )
            chosen = random.sample(self.positions, number_of_priorities)
            for priority, position in zip(Priority.values, chosen):
                internal_group_priority = None
                if applicant.status == ApplicantStatus.INTERVIEW_FINISHED:
                    internal_group_priority = random.choice(
                        InternalGroupStatus.values + [None]
                    )
                priorities.append(
                    InternalGroupPositionPriority(
                        applicant=applicant,
                        internal_group_position=position,
                        applicant_priority=priority,
                        internal_group_priority=internal_group_priority,
                    )
                )
        InternalGroupPositionPriority.objects.bulk_create(priorities)
        self.log(f"Created {len(priorities)} priorities")

    def fill_finished_interviews(self, applicants):
        finished = [
            a
            for a in applicants
            if a.status == ApplicantStatus.INTERVIEW_FINISHED and a.interview_id
        ]
        interview_ids = [a.interview_id for a in finished]
        interviews = list(Interview.objects.filter(id__in=interview_ids))

        interviewer_links = []
        for interview in interviews:
            interview.notes = INTERVIEW_NOTES_TEXT
            interview.discussion = INTERVIEW_DISCUSSION_TEXT
            interview.total_evaluation = random.choice(
                Interview.EvaluationOptions.values
            )
            interview.registered_at_samfundet = random.random() < 0.8
            for user in random.sample(self.users, min(len(self.users), 3)):
                interviewer_links.append(
                    Interview.interviewers.through(interview=interview, user=user)
                )
        Interview.objects.bulk_update(
            interviews,
            ["notes", "discussion", "total_evaluation", "registered_at_samfundet"],
        )
        Interview.interviewers.through.objects.bulk_create(interviewer_links)

        boolean_answers = list(
            InterviewBooleanEvaluationAnswer.objects.filter(
                interview_id__in=interview_ids
            )
        )
        for answer in boolean_answers:
            answer.value = random.choice([True, False])
        InterviewBooleanEvaluationAnswer.objects.bulk_update(boolean_answers, ["value"])

        additional_answers = list(
            InterviewAdditionalEvaluationAnswer.objects.filter(
                interview_id__in=interview_ids
            )
        )
        for answer in additional_answers:
            answer.answer = random.choice(
                InterviewAdditionalEvaluationAnswer.Options.values
            )
        InterviewAdditionalEvaluationAnswer.objects.bulk_update(
            additional_answers, ["answer"]
        )
        self.log(f"Filled {len(interviews)} finished interviews")

    def create_applicant_activity(self, applicants):
        """Comments, recommendations and interests for finished applicants"""
        finished = [
            a for a in applicants if a.status == ApplicantStatus.INTERVIEW_FINISHED
        ]
        internal_groups = list({p.internal_group for p in self.positions})
        comments, recommendations, interests = [], [], []
        for applicant in finished:
            for _ in range(random.choice([0, 0, 1, 2])):
                comments.append(
                    ApplicantComment(
                        applicant=applicant,
                        user=random.choice(self.users),
                        text=self.fake.sentence(nb_words=12),
                    )
                )
            if random.random() < 0.15:
                recommendations.append(
                    ApplicantRecommendation(
                        applicant=applicant,
                        recommended_by=random.choice(self.users),
                        internal_group=random.choice(internal_groups),
                        reasoning=self.fake.sentence(nb_words=10),
                    )
                )
            if random.random() < 0.1:
                position = random.choice(self.positions)
                interests.append(
                    ApplicantInterest(
                        applicant=applicant,
                        internal_group=position.internal_group,
                        position_to_be_offered=position,
                    )
                )
        ApplicantComment.objects.bulk_create(comments)
        ApplicantRecommendation.objects.bulk_create(recommendations)
        ApplicantInterest.objects.bulk_create(interests)
        self.log(
            f"Created {len(comments)} comments, {len(recommendations)} recommendations "
            f"and {len(interests)} interests"
        )
