import math
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
from graphql_relay import to_global_id
from admissions.models import ApplicantInterest


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
        with transaction.atomic():
            interview = Interview.objects.create(
                location=location,
                interview_start=datetime_cursor,
                interview_end=datetime_cursor + interview_duration,
                total_evaluation=None,
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

    # This now counts people who did not interview, we should probably have a
    # purge step when moving from open admission to discussion
    # maybe have this in its own mutation
    """
    Admission 
    Configure -> Open -> Discussing -> Locked -> Closed
    This should be a irreversible process and each step should imply some transition handling
    If we go from configure to open we create interview objects
    If we go from Open to Discussing we should delete all data on people who did not interview
    If we go from Discussing to Locked we throw error if we have not evaluated everyone
    If we go from locked to closed we create user accounts
    Should probably not send an email. When we call and say yes this should probably be its own table?
    I am missing some intermediary stage here
    """
    evaluated = all_priorities.filter(internal_group_priority__isnull=False).count()
    current_progress = int(math.ceil((evaluated / positions_to_fill) * 100))

    return InternalGroupApplicantsData(
        internal_group=internal_group,
        first_priorities=first_priorities,
        second_priorities=second_priorities,
        third_priorities=third_priorities,
        current_progress=current_progress,
        positions_to_fill=positions_to_fill,
    )


def priority_to_number(internal_group_position_priority_option):
    if internal_group_position_priority_option == InternalGroupStatus.WANT:
        return 100
    elif internal_group_position_priority_option == InternalGroupStatus.PROBABLY_WANT:
        return 90
    elif internal_group_position_priority_option == InternalGroupStatus.RESERVE:
        return 80
    elif internal_group_position_priority_option == InternalGroupStatus.INTERESTED:
        return 70
    else:
        return 0


def get_applicant_position_offer(applicant):
    """
    Accepts an applicant and returns the name of the internal group position
    they stand go receive if admitted
    """
    applicant_priorities = applicant.get_priorities
    for priority in applicant_priorities:
        if priority.internal_group_priority == InternalGroupStatus.WANT:
            return priority

    for priority in applicant_priorities:
        if priority.internal_group_priority == InternalGroupStatus.PROBABLY_WANT:
            return priority

    for priority in applicant_priorities:
        if priority.internal_group_priority == InternalGroupStatus.INTERESTED:
            return priority

    for priority in applicant_priorities:
        if priority.internal_group_priority == InternalGroupStatus.RESERVE:
            return priority

    interests = applicant.internal_group_interests.filter(
        position_to_be_offered__isnull=False
    )
    if interests > 1:
        raise Exception(f"{applicant.get_full_name} has more than one offer")

    interest = interests.first()

    if interest:
        return interest.position_to_be_offered

    raise Exception(f"Applicant {applicant.get_full_name} is not really wanted")


def get_applicants_who_will_be_accepted(admission):
    return admission.applicants.filter(will_be_admitted=True)


def get_applicant_interest_qs_with_offers(admission):
    return ApplicantInterest.objects.filter(
        applicant__admission=admission, position_to_be_offered__isnull=False
    )


def parse_applicant_interest_qs_to_gql_applicant_preview(applicant_interest_qs):
    from .schema import ApplicantPreview

    parsed_applicant_interests = []
    for applicant_interest in applicant_interest_qs:
        flattened_applicant_data = ApplicantPreview(
            id=to_global_id("ApplicantNode", applicant_interest.applicant.id),
            full_name=applicant_interest.applicant.get_full_name,
            phone=applicant_interest.applicant.phone,
            offered_internal_group_position_name=applicant_interest.position_to_be_offered.name,
            applicant_priority="N/A",
        )
        parsed_applicant_interests.append(flattened_applicant_data)
    return parsed_applicant_interests


def parse_applicant_qs_to_gql_applicant_preview(applicant_qs):
    from admissions.schema import ApplicantPreview

    parsed_applicant_list = []
    for applicant in applicant_qs:
        priority = get_applicant_position_offer(applicant)
        flattened_applicant_data = ApplicantPreview(
            id=to_global_id("ApplicantNode", applicant.id),
            full_name=applicant.get_full_name,
            phone=applicant.phone,
            offered_internal_group_position_name=priority.internal_group_position.name,
            applicant_priority=priority.applicant_priority,
        )
        parsed_applicant_list.append(flattened_applicant_data)

    return parsed_applicant_list


def admission_applicant_preview(admission):
    """
    Gets all Applicant and ApplicantInterest instances that will be
    offered a position in the provided admission and returns them
    as a parsed list of graphene.ObjectType ApplicantPreview objects.

    :param admission: An Admission model instance of the applicants we want to parse
    :returns: A list of applicants who will be given an offer
    """
    applicants = get_applicants_who_will_be_accepted(admission)
    # Then we expand this with applicants with interest.
    parsed_applicants = parse_applicant_qs_to_gql_applicant_preview(applicants)

    applicant_interests = get_applicant_interest_qs_with_offers(admission)
    parsed_applicant_interests = parse_applicant_interest_qs_to_gql_applicant_preview(
        applicant_interests
    )

    final_applicant_list = [*parsed_applicants, *parsed_applicant_interests]
    # Can consider re-ordering by name here
    return final_applicant_list


def get_admission_final_applicant_qs(admission):
    """
    Retrieves all applicants who will be joining KSG, including those who have been offered
    some other position.
    """
    applicants = get_applicants_who_will_be_accepted(admission)
    applicants_with_alternate_offer = admission.applicants.filter(
        internal_group_interests__position_to_be_offered__isnull=False
    )
    merged_queryset = applicants | applicants_with_alternate_offer
    return merged_queryset


def get_applicant_offered_position(applicant):
    """
    Accepts an Applicant model instance and returns the position they will be offered
    """

    applicant_priorities = applicant.get_priorities
    for priority in applicant_priorities:
        if priority.internal_group_priority == InternalGroupStatus.WANT:
            return priority.internal_group_position

    # No one explicitly wants them, lets check if they are considered a reserve
    for priority in applicant_priorities:
        if priority.internal_group_priority == InternalGroupStatus.RESERVE:
            return priority.internal_group_position

    # Still nothing, maybe they have been offered a position
    applicant_interests = applicant.internal_group_interests.all()

    # There should only be one valid offer
    if applicant_interests.count() > 1:
        raise Exception(
            f"Applicant {applicant.get_full_name} has more than one registered offer, should only be one"
        )

    interest = applicant_interests.first()
    if not interest:
        raise Exception(
            f"Applicant {applicant.get_full_name} is not wanted by anyone. Why are they in this list?"
        )

    return interest.position_to_be_offered
