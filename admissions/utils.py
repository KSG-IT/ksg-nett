from django.utils import timezone
from django.db import transaction
from common.util import send_email
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.apps import apps
import csv
from common.util import date_time_combiner


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

    # Lazy load model due to circular import errors
    Interview = apps.get_model(app_label="admissions", model_name="Interview")

    while datetime_cursor < datetime_interview_period_end:
        print(f"{datetime_cursor}")
        # Generate interviews for the first session of the day
        for i in range(schedule.default_block_size):
            available_locations = get_available_interview_locations(
                datetime_from=datetime_cursor,
                datetime_to=datetime_cursor + interview_duration,
            )
            print(f"{available_locations.count()} locations are available")
            for location in available_locations:
                print(
                    f"Looking at {location} from {datetime_cursor} to {datetime_cursor + interview_duration}"
                )
                Interview.objects.create(
                    location=location,
                    interview_start=datetime_cursor,
                    interview_end=datetime_cursor + interview_duration,
                )
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
                with transaction.atomic():
                    Interview.objects.create(
                        location=location,
                        interview_start=datetime_cursor,
                        interview_end=datetime_cursor + interview_duration,
                    )

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
