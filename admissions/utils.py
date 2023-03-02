import math

import pytz
from django.utils import timezone
from django.db import transaction
from graphene_django_cud.util import disambiguate_id

from common.util import send_email
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.apps import apps

from common.util import (
    date_time_combiner,
    get_date_from_datetime,
    parse_datetime_to_midnight,
    validate_qs,
)
from admissions.consts import InternalGroupStatus, Priority, ApplicantStatus
from graphql_relay import to_global_id
from admissions.models import (
    ApplicantInterest,
    Applicant,
    InternalGroupPositionPriority,
)
from organization.models import InternalGroupPosition


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

    datetime_cursor = timezone.make_aware(
        timezone.datetime(
            year=interview_period_start_date.year,
            month=interview_period_start_date.month,
            day=interview_period_start_date.day,
            hour=default_interview_day_start.hour,
            minute=default_interview_day_start.minute,
            second=0,
        ),
        timezone=pytz.timezone(settings.TIME_ZONE),
    )
    datetime_interview_period_end = timezone.make_aware(
        timezone.datetime(
            year=schedule.interview_period_end_date.year,
            month=schedule.interview_period_end_date.month,
            day=schedule.interview_period_end_date.day,
            hour=default_interview_day_end.hour,
            minute=default_interview_day_end.minute,
            second=0,
        ),
        timezone=pytz.timezone(settings.TIME_ZONE),
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


def send_applicant_notice_email(applicant):
    content = _(
        f"""
                Hei!
                
                Vi ser at du har søkt KSG og det har gått litt tid siden vi sist
                har hørt fra deg. 
    
                Lenke: {settings.APP_URL}/applicant-portal/{applicant.token}
                """
    )

    html_content = _(
        f"""
            Hei!
            <br />
            <br />                
            Vi ser at du har søkt KSG og det har gått litt tid siden vi sist har hørt fra deg.
            <br /> 
            Trykk på denne linken for å få tilsendt innloggingsinformasjon.
            <br />
            <span>{settings.APP_URL}/applicant-portal/{applicant.token}</span>
            <br />
        """
    )

    return send_email(
        _("Intervju KSG"),
        message=content,
        html_message=html_content,
        recipients=[applicant.email],
    )


def mass_send_welcome_to_interview_email(emails):
    """
    Accepts a list of emails and sends the same email ass bcc to all the recipients.
    Main advantage here is that we do not need to batch together 150 emails which causes
    timeouts and slow performance. The applicant can then instead request to be sent their
    custom auth token from the portal itself.
    """
    content = _(
        f"""
                            Hei og takk for at du søker KSG!
            
                            Trykk på denne linken for å få tilsendt innloggingsinformasjon.
            
                            Lenke: {settings.APP_URL}/applicant-portal
                            """
    )

    html_content = _(
        f"""
            Hei og takk for at du søker KSG!
            <br />
            <br />
            Trykk på denne linken for å få tilsendt innloggingsinformasjon.
            <br />
            {settings.APP_URL}/applicant-portal
            <br />
        """
    )

    return send_email(
        _("Intervju KSG"),
        message=content,
        html_message=html_content,
        recipients=[],
        bcc=emails,
    )


def send_welcome_to_interview_email(email: str, auth_token: str):
    content = _(
        f"""
            Hei og velkommen til intervju hos KSG!
            
            Du får nå silsendt en lenke som lar deg registrere personlige opplysninger,
            hvilket verv du er interessert i hos oss og velge et intervjutidspunkt som passer
            deg.
        
            Trykk på denne linken for å registrere søknaden videre
        
            Lenke: {settings.APP_URL}/applicant-portal/{auth_token}
            """
    )

    html_content = _(
        f"""
            Hei og velkommen til intervju hos KSG! 
            <br />
            <br />
            Du får nå silsendt en lenke som lar deg registrere personlige opplysninger,
            hvilket verv du er interessert i hos oss og velge et intervjutidspunkt som passer
            deg.
            <br />
            {settings.APP_URL}/applicant-portal/{auth_token}
            <br />
            """
    )

    return send_email(
        _("Intervju KSG"),
        message=content,
        html_message=html_content,
        recipients=[email],
    )


def resend_auth_token_email(applicant):
    content = _(
        f"""
            Hei og velkommen til KSG sin søkerportal! 
    
            Trykk på denne linken for å registrere søknaden videre, eller se intervjutiden din.
    
            Lenke: {settings.APP_URL}/applicant-portal/{applicant.token}
            """
    )

    html_content = _(
        f"""
                Hei og velkommen til KSG sin søkerportal! 
                <br />
                Trykk på denne linken for å registrere søknaden videre, eller se intervjutiden din.
                <br />
                {settings.APP_URL}/applicant-portal/{applicant.token}
                <br />
            """
    )

    return send_email(
        _("KSG søkerportal"),
        message=content,
        html_message=html_content,
        recipients=[applicant.email],
    )


def send_new_interview_mail(applicant):
    content = _(
        f"""
                Hei!
                
                Du har fått en ny intervjutid hos KSG. 
                
                Lenke: {settings.APP_URL}/applicant-portal/{applicant.token}
            """
    )

    html_content = _(
        f"""
                Hei!
                <br />
                Du har fått en ny intervjutid hos KSG. 
                <br />
                {settings.APP_URL}/applicant-portal/{applicant.token}
                <br />
            """
    )

    return send_email(
        _("Oppdatert intervju KSG"),
        message=content,
        html_message=html_content,
        recipients=[applicant.email],
    )


def send_interview_cancelled_email(applicant):
    content = _(
        """
            Hei!
            
            Ditt intervju hos KSG har blitt kansellert. 
            
            """
    )

    html_content = _(
        """
            Hei!
            <br />
            Ditt intervju hos KSG har blitt kansellert. 
            <br />
            """
    )

    return send_email(
        _("Kansellert intervju KSG"),
        message=content,
        html_message=html_content,
        recipients=[applicant.email],
    )


def notify_interviewers_cancelled_interview_email(applicant, interview):
    local_time = timezone.localtime(
        interview.interview_start, pytz.timezone(settings.TIME_ZONE)
    )
    name = applicant.get_full_name
    interview_location = interview.location.name
    formatted_local_time = local_time.strftime("%d.%m.%Y kl. %H:%M")
    content = (
        _(
            """
                Hei!
                
                %(name)s har kansellert sitt intervju hos KSG. 
                
                Du har blitt fjernet fra intervjuet.
    
                Intervjuinformasjon:
                %(interview_location)s
                %(interview_time)s
                
                """
        )
        % {
            "name": name,
            "interview_location": interview_location,
            "interview_time": formatted_local_time,
        }
    )

    html_content = (
        _(
            """
                Hei!
                <br />
                %(name)s har kansellert sitt intervju hos KSG. 
                <br />
                Du har blitt fjernet fra intervjuet.
                <br />
                Intervjuinformasjon:
                <br />
                %(interview_location)s
                <br />
                %(interview_time)s
                <br />
                
                """
        )
        % {
            "name": name,
            "interview_location": interview_location,
            "interview_time": formatted_local_time,
        }
    )

    return send_email(
        _("Kansellert intervju KSG"),
        message=content,
        html_message=html_content,
        recipients=[],
        bcc=interview.interviewers.values_list("email", flat=True),
    )


def notify_interviewers_applicant_has_been_removed_from_interview_email(
    applicant, interview
):
    local_time = timezone.localtime(
        interview.interview_start, pytz.timezone(settings.TIME_ZONE)
    )
    name = applicant.get_full_name
    interview_location = interview.location.name
    formatted_local_time = local_time.strftime("%d.%m.%Y kl. %H:%M")
    content = (
        _(
            """
                Hei!
                
                %(name)s har blitt fjernet fra sitt intervju hos KSG. 
                
                Intervjuere har blitt fjernet fra intervjuet.
    
                Intervjuinformasjon:
                %(interview_location)s
                %(interview_time)s
                
                """
        )
        % {
            "name": name,
            "interview_location": interview_location,
            "interview_time": formatted_local_time,
        }
    )

    html_content = (
        _(
            """
                Hei!
                <br />
                %(name)s har blitt fjernet fra sitt intervju hos KSG. 
                <br />
                Intervjuere har blitt fjernet fra intervjuet.
                <br />
                Intervjuinformasjon:
                <br />
                %(interview_location)s
                <br />
                %(interview_time)s
                <br />
                
                """
        )
        % {
            "name": name,
            "interview_location": interview_location,
            "interview_time": formatted_local_time,
        }
    )

    return send_email(
        _("Fjernet fra intervju KSG"),
        message=content,
        html_message=html_content,
        recipients=[applicant.email],
        bcc=interview.interviewers.values_list("email", flat=True),
    )


def send_interview_confirmation_email(interview):
    applicant = interview.applicant

    local_time = timezone.localtime(
        interview.interview_start, pytz.timezone(settings.TIME_ZONE)
    )
    name = applicant.get_full_name
    interview_location = interview.location.name
    formatted_local_time = local_time.strftime("%d.%m.%Y kl. %H:%M")
    content = (
        _(
            """
            Hei!
            
            Så gøy at du vil på intervju hos KSG:)
            Dette er en bekreftelse på at du har fått et intervju hos KSG.
            
            Intervjuinformasjon:
            %(interview_location)s
            %(interview_time)s
            Møt opp i glassinngangen til Samfundet fem minutter før intervjuet starter. 
            Vi ser frem til å møte deg! 
            
            
            Om du har huket av på digitalt intervju vil du få tilsendt en lenke ved intervjustart og
            kan se bort fra beskjed om å møte opp ved glaassinngangen.

            Om du har noen spørsmål, send en mail til ksg-opptak@samfundet.no 
            """
        )
        % {
            "name": name,
            "interview_location": interview_location,
            "interview_time": formatted_local_time,
        }
    )

    html_content = (
        _(
            """
            Hei!
            <br />
            Dette er en bekreftelse på at du har fått et intervju hos KSG.
            <br />
            Intervjuinformasjon:
            <br />
            %(interview_location)s
            <br />
            %(interview_time)s
            <br />
            
            Møt opp i glassinngangen til Samfundet fem minutter før intervjuet starter.
            <br />
            Vi ser frem til å møte deg!
            <br />
            
            Om du har huket av på digitalt intervju vil du få tilsendt en lenke ved intervjustart og
            kan se bort fra beskjed om å møte opp ved glaassinngangen.
            <br />
            Om du har noen spørsmål, send en mail til ksg-opptak@samfundet.no
            <br />
            
            
            """
        )
        % {
            "name": name,
            "interview_location": interview_location,
            "interview_time": formatted_local_time,
        }
    )

    return send_email(
        _("Bekreftelse intervju KSG"),
        message=content,
        html_message=html_content,
        recipients=[applicant.email],
    )


def read_admission_csv(file):
    """
    This handler could be subjects to change depending on how MG-web changes the portal. Currently the column headers
    are Navn, Telefon, E-postadresse, Campus, Stilling, Intervjutid, Intervjusted, Prioritet, Status, Kommentar.
    An applicant has an entry for each position they apply for. This means that we can have duplication of
    name, email and phone number.
        > Save a row number cursor and then the csv can just be re-uploaded?
        > Has to be very robust aginst user input
    """
    from admissions.models import Applicant
    from users.models import User

    applicants = []
    email_tracker = []
    decoded_file = file.read().decode("utf-8")
    lines = decoded_file.split("\n")
    for row in lines[1:]:
        if row == "":
            break

        # We respect the user's capitalization of their email
        email = row.split(",")[2].strip()
        row = row.lower()
        cells = row.split(",")

        cells = [cell.strip() for cell in cells]
        name = cells[0]
        name_split = name.split(" ")

        # Remove any items in the list which are just an empty space
        cleaned_name_split = [x for x in name_split if x != ""]
        # Want to capitalize the first letter of every string
        parsed_name_split = [word[0].upper() + word[1:] for word in cleaned_name_split]

        # Only caveat are any names brought together with a '-', like Anne-Marie -> Anne-marie
        last_name = parsed_name_split[-1]
        first_name = " ".join(parsed_name_split[:-1])

        phone_number = cells[1]

        if email in email_tracker:
            # We use this as a unique identifier for the applicant.
            # An applicant has a row for each position they apply for.
            continue

        if (
            Applicant.objects.filter(email=email).exists()
            or User.objects.filter(email=email).exists()
        ):
            # Not sure if we should keep it implicit like this?
            continue

        applicant_data = {
            "name": f"{first_name} {last_name}",
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone_number,
            "email": email,
        }
        applicants.append(applicant_data)
        email_tracker.append(email)

    return applicants


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
        applicant.email = fake_data.email
        applicant.address = fake_data.address[:20]
        applicant.hometown = fake_data.hometown[:20]
        applicant.phone = fake_data.phone[:10]
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
            interview_group = Interview.objects.filter(
                interview_start=cursor, applicant__isnull=True
            )
            slot = {"timestamp": cursor, "interviews": interview_group}
            day_groupings.append(slot)
            cursor += inferred_interview_duration

        interview_day = {"date": day["date"], "groupings": day_groupings}
        parsed_interviews.append(interview_day)

    return parsed_interviews


def internal_group_applicant_data(internal_group):
    """
    Accepts an internal group and retrieves its admission data. This is explicitly used
    for the dashboard where interviewers assign themselves to interviews. Not to be
    confused with the Discussion Data.
    """
    from admissions.schema import InternalGroupApplicantsData

    Applicant = apps.get_model(app_label="admissions", model_name="Applicant")
    Admission = apps.get_model(app_label="admissions", model_name="Admission")
    InternalGroupPositionPriority = apps.get_model(
        app_label="admissions", model_name="InternalGroupPositionPriority"
    )
    active_admission = Admission.get_active_admission()
    all_applicants = Applicant.objects.filter(admission=active_admission)

    # Is it possible to sort by and append all that are null
    first_priorities = (
        all_applicants.filter(
            priorities__applicant_priority=Priority.FIRST,
            priorities__internal_group_position__internal_group=internal_group,
        )
        .exclude(status=ApplicantStatus.RETRACTED_APPLICATION)
        .order_by("first_name")
    )
    second_priorities = (
        all_applicants.filter(
            priorities__applicant_priority=Priority.SECOND,
            priorities__internal_group_position__internal_group=internal_group,
        )
        .exclude(status=ApplicantStatus.RETRACTED_APPLICATION)
        .order_by("first_name")
    )
    third_priorities = (
        all_applicants.filter(
            priorities__applicant_priority=Priority.THIRD,
            priorities__internal_group_position__internal_group=internal_group,
        )
        .exclude(status=ApplicantStatus.RETRACTED_APPLICATION)
        .order_by("first_name")
    )

    all_priorities = InternalGroupPositionPriority.objects.filter(
        internal_group_position__internal_group=internal_group
    )

    admission = Admission.get_active_admission()
    data = admission.available_internal_group_positions_data.filter(
        internal_group_position__internal_group=internal_group
    ).first()
    positions_to_fill = data.available_positions

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
        mvp_list=[],  # TODO
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
    applicant_priorities = [priority for priority in applicant_priorities if priority]

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
            applicant_priority="None",
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
    Accepts an Applicant model instance and returns the position they will be offered.
    """

    applicant_priorities = applicant.get_priorities
    applicant_priorities = [priority for priority in applicant_priorities if priority]

    for priority in applicant_priorities:
        if priority.internal_group_priority == InternalGroupStatus.WANT:
            return priority.internal_group_position

    # No one explicitly wants them, lets check if they are considered a reserve
    for priority in applicant_priorities:
        if priority.internal_group_priority == InternalGroupStatus.RESERVE:
            return priority.internal_group_position

    # Still nothing, maybe they have been offered a position
    applicant_interests = applicant.internal_group_interests.filter(
        position_to_be_offered__isnull=False
    )

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


def get_applicant_priority_list(priority_order):
    trimmed_global_ids = []
    for priority_order_id in priority_order:
        if not priority_order_id:
            continue
        trimmed_global_ids.append(priority_order_id)

    position_ids = [disambiguate_id(global_id) for global_id in trimmed_global_ids]
    return InternalGroupPosition.objects.filter(id__in=position_ids)


def construct_new_priority_list(priority_order):
    priority_order = [disambiguate_id(global_id) for global_id in priority_order]
    return [InternalGroupPosition.objects.get(id=id) for id in priority_order]


def remove_applicant_choice(applicant, internal_group_position):
    priorities = [Priority.FIRST, Priority.SECOND, Priority.THIRD]
    unfiltered_priorities = applicant.get_priorities
    filtered_priorities = []
    # Unfiltered priorities can have None values. Get rid of them
    for priority in unfiltered_priorities:
        if not priority:
            continue
        # We don't want to re-add the position we are trying to delete
        if priority.internal_group_position == internal_group_position:
            continue

        filtered_priorities.append(priority.internal_group_position)

    # Delete the priorities so we can add them in the right order
    applicant.priorities.all().delete()
    for element in filtered_priorities:
        applicant.add_priority(element)
    applicant.save()


def interview_overview_parser(interviews):
    """
    Accepts a queryset of interviews and formats them to an easiuly digestible format used by
    the timetable on the frontend.

      {
        location: 'bodegaen',
        interviews: [
          {
            time: '10:30',
            name: 'Ola Nordmann',
          },
          {
            time: '14:00',
            name: '',
          },
        ],
      },
    """
    from .schema import InterviewOverviewCell, InterviewLocationOverviewRow
    from .models import InterviewLocation

    locations = InterviewLocation.objects.all().order_by("name")

    result = []
    for location in locations:
        filtered_interviews = interviews.filter(location=location)
        interviews_cells = []
        for interview in filtered_interviews:
            name = "Ledig"
            applicant_id = None
            if interview.get_applicant:
                name = interview.applicant.get_full_name
                applicant_id = to_global_id("ApplicantNode", interview.applicant.id)

            local_time = timezone.localtime(
                interview.interview_start, pytz.timezone(settings.TIME_ZONE)
            )

            minute = str(local_time.minute)
            if len(minute) == 1:
                minute = f"0{minute}"

            hour = str(local_time.hour)
            if len(hour) == 1:
                hour = f"0{hour}"

            time = f"{hour}:{minute}"

            cell = InterviewOverviewCell(
                time=time,
                content=name,
                color="#FF0000" if interview.get_applicant else "#00FF00",
                interview_id=to_global_id("InterviewNode", interview.id),
                applicant_id=applicant_id,
            )
            interviews_cells.append(cell)

        if not interviews_cells:
            continue

        row = InterviewLocationOverviewRow(
            location=location.name,
            interviews=interviews_cells,
        )

        result.append(row)

    # locations and result should be synced
    return result, locations


def add_evaluations_to_interview(interview):

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

    boolean_evaluation_statements = InterviewBooleanEvaluation.objects.all()
    additional_evaluation_statements = (
        InterviewAdditionalEvaluationStatement.objects.all()
    )
    for statement in boolean_evaluation_statements:
        InterviewBooleanEvaluationAnswer.objects.create(
            interview=interview, statement=statement, value=None
        )
    for statement in additional_evaluation_statements:
        InterviewAdditionalEvaluationAnswer.objects.create(
            interview=interview, statement=statement, answer=None
        )

    interview.save()


def get_interview_statistics(admission):
    from .schema import InterviewStatistics, UserInterviewCount
    from users.models import User
    from .models import Interview

    interviews = Interview.objects.filter(applicant__admission=admission)
    total_applicants = admission.applicants.count()
    total_booked_interviews = interviews.filter(
        applicant__isnull=False, applicant__status=ApplicantStatus.SCHEDULED_INTERVIEW
    ).count()
    total_finished_interviews = interviews.filter(
        applicant__isnull=False, applicant__status=ApplicantStatus.INTERVIEW_FINISHED
    ).count()

    now = timezone.now()
    total_available_interviews = Interview.objects.filter(
        applicant__isnull=True, interview_start__gte=now
    ).count()

    user_interview_counts = []
    users = (
        User.objects.filter(interviews_attended__applicant__admission=admission)
        .distinct()
        .prefetch_related("interviews_attended")
    )
    for user in users:
        user_interview_counts.append(
            UserInterviewCount(
                user=user,
                interview_count=user.interviews_attended.filter(
                    applicant__admission=admission
                ).count(),
            )
        )

    user_interview_counts.sort(key=lambda x: x.interview_count, reverse=True)

    return InterviewStatistics(
        total_applicants=total_applicants,
        total_booked_interviews=total_booked_interviews,
        total_finished_interviews=total_finished_interviews,
        total_available_interviews=total_available_interviews,
        user_interview_counts=user_interview_counts,
    )
