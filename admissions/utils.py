from django.utils import timezone
from django.db import transaction
from common.util import send_email
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.apps import apps
import csv
from common.util import (
    date_time_combiner,
    get_date_from_datetime,
    parse_datetime_to_midnight,
    validate_qs,
)
from admissions.consts import InternalGroupStatus, Priority


def get_available_interview_locations(datetime_from=None, datetime_to=None):
    """
    Accepts a date range and returns all InterviewLocation instances which are available in the given timespan.
    If this helper does not return any instances it probably is due to a lack of InterviewLocationAvailability
    instances with valid date ranges
    """

    if not (datetime_from or datetime_to):
        raise ValueError("Arguments cannot be None")

    if datetime_from > datetime_to:
        raise ValueError(
            "Invalid date range, datetime_from is greater than datetime_to"
        )

    # Lazy load model due to circular import errors
    InterviewLocation = apps.get_model(
        app_label="admissions", model_name="InterviewLocation"
    )
    return InterviewLocation.objects.filter(
        availability__datetime_from__lte=datetime_from,
        availability__datetime_to__gte=datetime_to,
    ).distinct()


def generate_interviews_from_schedule(schedule):
    # Double check if this thing does what its supposed to do
    def generate_interview_and_evaluations_for_location(location):
        with transaction.atomic:
            interview = Interview.objects.create(
                location=location,
                interview_start=datetime_cursor,
                interview_end=datetime_cursor + interview_duration,
            )
            for statement in boolean_evaluation_statements:
                InterviewBooleanEvaluationAnswer.objects.create(
                    interview=interview, statement=statement, value=None
                )
            for statement in additional_evaluation_statements:
                InterviewAdditionalEvaluationAnswer.objects.create(
                    interview=interview, statement=statement, answer=None
                )

    interview_duration = schedule.default_interview_duration
    default_pause_duration = schedule.default_pause_duration
    default_interview_day_start = schedule.default_interview_day_start
    default_interview_day_end = schedule.default_interview_day_end
    interview_period_start_date = schedule.interview_period_start_date

    datetime_cursor = date_time_combiner(
        interview_period_start_date, default_interview_day_start
    )
    datetime_interview_period_end = date_time_combiner(
        schedule.interview_period_end_date, default_interview_day_end
    )

    # Lazy load models due to circular import errors
    Interview = apps.get_model(app_label="admissions", model_name="Interview")
    InterviewBooleanEvaluation = apps.get_model(
        app_label="admissions", model_name="InterviewBooleanEvaluation"
    )
    InterviewBooleanEvaluationAnswer = apps.get_model(
        app_label="admissions", model_name="InterviewBooleanEvaluationAnswer"
    )
    InterviewAdditionalEvaluationStatement = apps.get_model(
        app_label="admissions", model_name="InterviewAdditionalEvaluationStatement"
    )
    InterviewAdditionalEvaluationAnswer = apps.get_model(
        app_label="admissions", model_name="InterviewAdditionalEvaluationAnswer"
    )

    # We want to prepare the interview questions and add them to all interviews
    boolean_evaluation_statements = InterviewBooleanEvaluation.objects.all()
    additional_evaluation_statements = (
        InterviewAdditionalEvaluationStatement.objects.all()
    )
    while datetime_cursor < datetime_interview_period_end:
        # Generate interviews for the first session of the day
        for i in range(schedule.default_block_size):
            available_locations = get_available_interview_locations(
                datetime_from=datetime_cursor,
                datetime_to=datetime_cursor + interview_duration,
            )
            for location in available_locations:
                generate_interview_and_evaluations_for_location(location)
            datetime_cursor += interview_duration

        # First session is over. We give the interviewers a break
        datetime_cursor += default_pause_duration

        # Generate the other half of the interviews for the day
        for i in range(schedule.default_block_size):
            available_locations = get_available_interview_locations(
                datetime_from=datetime_cursor,
                datetime_to=datetime_cursor + interview_duration,
            )
            for location in available_locations:
                generate_interview_and_evaluations_for_location(location)

            datetime_cursor += interview_duration

        # Interviews for the day is over. Update cursor.
        datetime_cursor += timezone.timedelta(days=1)
        datetime_cursor = timezone.make_aware(
            timezone.datetime(
                year=datetime_cursor.year,
                month=datetime_cursor.month,
                day=datetime_cursor.day,
                hour=default_interview_day_start.hour,
                minute=default_interview_day_start.minute,
                second=0,
            )
        )


def mass_send_welcome_to_interview_email(emails):
    """
    Accepts a list of emails and sends the same email ass bcc to all the recipients.
    Main advantage here is that we do not need to batch together 150 emails which causes
    timeouts and slow performance. The applicant can then instead request to be sent their
    custom auth token from the portal itself.
    """
    content = (
        _(
            """
                    Hei og velkommen til intervju hos KSG!
    
                    Trykk på denne linken for å registrere søknaden videre
    
                    Lenke: %(link)s
                    """
        )
        % {"link": f"{settings.APP_URL}/applicant-portal"}
    )

    html_content = (
        _(
            """
                    Hei og velkommen til intervju hos KSG! 
                    <br />
                    <br />
                    Trykk på denne linken for å registrere søknaden videre
                    <br />
                    <a href="%(link)s">Registrer søknad</a><br />
                    <br />
                    """
        )
        % {"link": f"{settings.APP_URL}/applicant-portal"}
    )

    return send_email(
        _("Intervju KSG"),
        message=content,
        html_message=html_content,
        recipients=[],
        bcc=emails,
    )


def send_welcome_to_interview_email(email: str, auth_token: str):
    content = (
        _(
            """
                            Hei og velkommen til intervju hos KSG!
                        
                            Trykk på denne linken for å registrere søknaden videre
                        
                            Lenke: %(link)s
                            """
        )
        % {"link": f"{settings.APP_URL}/applicant-portal/{auth_token}"}
    )

    html_content = (
        _(
            """
                                Hei og velkommen til intervju hos KSG! 
                                <br />
                                <br />
                                Trykk på denne linken for å registrere søknaden videre
                                <br />
                                <a href="%(link)s">Registrer søknad</a><br />
                                <br />
                            """
        )
        % {"link": f"{settings.APP_URL}/applicant-portal/{auth_token}"}
    )

    return send_email(
        _("Intervju KSG"),
        message=content,
        html_message=html_content,
        recipients=[email],
    )


def resend_auth_token_email(applicant):
    content = (
        _(
            """
                    Hei og velkommen til KSG sin søkerportal! 
            
                    Trykk på denne linken for å registrere søknaden videre, eller se intervjutiden din.
            
                    Lenke: %(link)s
                    """
        )
        % {"link": f"{settings.APP_URL}/applicant-portal/{applicant.token}"}
    )

    html_content = (
        _(
            """
                    Hei og velkommen til KSG sin søkerportal! 
                    <br />
                    Trykk på denne linken for å registrere søknaden videre, eller se intervjutiden din.
                    <br />
                    <a href="%(link)s">Registrer søknad</a><br />
                    <br />
                    """
        )
        % {"link": f"{settings.APP_URL}/applicant-portal/{applicant.token}"}
    )

    return send_email(
        _("KSG søkerportal"),
        message=content,
        html_message=html_content,
        recipients=[applicant.email],
    )


def read_admission_csv(file):
    """
    This handler could be subjects to change depending on how MG-web changes the portal. Currently the column headers
    are Navn, Telefon, E-postadresse, Campus, Stilling, Intervjutid, Intervjusted, Prioritet, Status, Kommentar.
    An applicant has an entry for each position they apply for. This means that we can have duplication of
    name, email and phone number. If we want to automate this spreadsheet we should handle this in some manner.
        > Save a row number cursor and then the csv can just be re-uploaded?
        > Has to be very robust aginst user input
    """
    with open(file, newline="") as csv_file:
        admission = csv.reader(csv_file, delimiter=",")
        header = next(admission)
        for row in admission:
            name = row[0]
            phone_number = row[1]
            email = row[2]
            stilling = row[4]


def obfuscate_admission(admission):
    """
    Obfuscates all applications for a given admission process. Meaning removing any identifying information.
    Randomizes name, phone number and email. Other details we can use to track statistics.
    """
    # Lazy load it due to circular import issues
    from admissions.tests.factories import ApplicantFactory

    for applicant in admission.applicants.all():
        # Write a fucking test case
        fake_data = ApplicantFactory.build(admission=admission)
        applicant.first_name = fake_data.first_name
        applicant.last_name = fake_data.last_name
        applicant.address = fake_data.address
        applicant.phone = fake_data.phone
        applicant.save()


def group_interviews_by_date(interviews):
    """
    We accept a queryset and sort it into a list of groupings. Each item in the list is a dict which has a
    day defined through a date object and a list of interviews that occur on this date.

    Example:
        [
            {
                "date": 2022-24-02,
                "interviews": [Interview1, Interview2, ...]
            },
            {
                "date": 2022-25-02,
                "interviews": [Interview1, Interview2, ...]
            }
            ...
        ]
    """
    validate_qs(interviews)

    interviews = interviews.order_by("interview_start")
    interview_sample = interviews.first()
    if not interview_sample:
        return []
    cursor = parse_datetime_to_midnight(interview_sample.interview_start)
    cursor_end = interviews.last().interview_start
    day_offset = timezone.timedelta(days=1)
    interview_groupings = []

    while cursor <= cursor_end:
        grouping = interviews.filter(
            interview_start__gte=cursor, interview_start__lte=cursor + day_offset
        )
        if grouping:
            interview_groupings.append(
                {"date": get_date_from_datetime(cursor), "interviews": grouping}
            )
        cursor += day_offset
    return interview_groupings


def create_interview_slots(interview_days):
    """
    Input is assumed to be a list of dictionary objects with a 'date' and 'interviews' keys. The interviews object
    are ordered in ascending order. We return a nested structure which groups together days with interviews
    in addition to grouping interviews that have the same timeframe together.
    """
    from admissions.models import Interview  # Avoid circular import error

    if not interview_days:
        return []

    first_interview = interview_days[0]["interviews"][0]
    if not first_interview:
        return []

    # We use the inferred duration as our cursor offset
    inferred_interview_duration = (
        first_interview.interview_end - first_interview.interview_start
    )
    parsed_interviews = []

    for day in interview_days:
        interviews = day["interviews"]
        last_interview = interviews.last().interview_end

        if not interviews:
            continue

        cursor = interviews[0].interview_start
        day_groupings = []
        while cursor < last_interview:
            # Interviews are always created in parallel. Meaning we can use the exact datetime to filter
            interview_group = Interview.objects.filter(interview_start=cursor)
            slot = {"timestamp": cursor, "interviews": interview_group}
            day_groupings.append(slot)
            cursor += inferred_interview_duration

        interview_day = {"date": day["date"], "groupings": day_groupings}
        parsed_interviews.append(interview_day)

    return parsed_interviews


def internal_group_applicant_data(internal_group):
    """
    Accepts an internal group and retrieves its admission data
    """
    from admissions.schema import InternalGroupApplicantsData

    Applicant = apps.get_model(app_label="admissions", model_name="Applicant")
    Admission = apps.get_model(app_label="admissions", model_name="Admission")
    InternalGroupPositionPriority = apps.get_model(
        app_label="admissions", model_name="InternalGroupPositionPriority"
    )

    first_priorities = Applicant.objects.filter(
        priorities__applicant_priority=Priority.FIRST,
        priorities__internal_group_position__internal_group=internal_group,
    ).order_by("interview__interview_start")
    second_priorities = Applicant.objects.filter(
        priorities__applicant_priority=Priority.SECOND,
        priorities__internal_group_position__internal_group=internal_group,
    ).order_by("interview__interview_start")
    third_priorities = Applicant.objects.filter(
        priorities__applicant_priority=Priority.THIRD,
        priorities__internal_group_position__internal_group=internal_group,
    ).order_by("interview__interview_start")

    all_priorities = InternalGroupPositionPriority.objects.filter(
        internal_group_position__internal_group=internal_group
    )

    want_count = all_priorities.filter(
        internal_group_priority=InternalGroupStatus.WANT
    ).count()

    admission = Admission.get_active_admission()
    data = admission.available_internal_group_positions_data.filter(
        internal_group_position__internal_group=internal_group
    ).first()
    positions_to_fill = data.available_positions

    return InternalGroupApplicantsData(
        internal_group=internal_group,
        first_priorities=first_priorities,
        second_priorities=second_priorities,
        third_priorities=third_priorities,
        current_progress=want_count,
        positions_to_fill=positions_to_fill,
    )
