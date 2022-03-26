import random
import re
from io import BytesIO
from sys import getsizeof
from datetime import datetime, date
from typing import Union, List, Tuple
from PIL import Image
from pydash import strip_tags
from django.core.mail import send_mail, EmailMultiAlternatives, get_connection
from graphql_relay import from_global_id

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils import timezone
from django.db.models import QuerySet


def get_semester_year_shorthand(timestamp: Union[datetime, date]) -> str:
    """
    get_semester_year_shortand renders the `timestamp` attribute into a "semester-year"-representation.
    Examples:
        2018-01-01 => V18
        2014-08-30 => H14
        2012-12-30 => H12
    :return: The "semeter-year" display of the `timestamp` attribute.
    """
    if not timestamp:
        return ""
    short_year_format = str(timestamp.year)[2:]
    semester_prefix = "H" if timestamp.month > 7 else "V"
    return f"{semester_prefix}{short_year_format}"


def get_semester_year_shorthands_by_date(timestamp: Union[datetime, date]) -> List[str]:
    """
    get_semester_year_shorthands_by_date gets a list of semester-year shorthands backwards
    in time. The earliest shorthand is defined by the semester the given timestamp occurs in.

    Example:
        timestamp = 12/04/2015, timezone.now → 25/05/2018
        result: [
            "V18",
            "H17",
            "V17",
            "H16",
            "V16",
            "H15",
            "V15"
        ]

    :param timestamp:
    :return:
    """
    now = timezone.now()
    current_semester_shorthand = get_semester_year_shorthand(now)
    target_semester_shorthand = get_semester_year_shorthand(timestamp)

    semester, year = current_semester_shorthand[0], int(current_semester_shorthand[1:])
    target_semester, target_year = target_semester_shorthand[0], int(
        target_semester_shorthand[1:]
    )

    if timestamp.year > now.year or (
        timestamp.year == now.year and target_semester < semester
    ):  # H < V alphabetically, and hence in the comparison
        return []

    results = [current_semester_shorthand]
    while semester != target_semester or year != target_year:
        year = year if semester == "H" else 99 if year == 0 else year - 1
        semester = "V" if semester == "H" else "H"
        results.append(f"{semester}{str(year).zfill(2)}")

    return results


def get_semester_year_shorthands_by_count(number: int) -> List[str]:
    """
    get_semester_year_shorthands_by_count returns `number` amount of semester-year shorthands
    backwards in time.

    Example:
        number = 3, timezone.now → 25/05/2018
        result: ["V18", "H17", "V17"]

    :param number:
    :return:
    """
    if number <= 0:
        return []

    current_semester_shorthand = get_semester_year_shorthand(timezone.now())
    semester, year = current_semester_shorthand[0], int(current_semester_shorthand[1:])

    results = [current_semester_shorthand]

    while number > 1:
        number -= 1
        year = year if semester == "H" else 99 if year == 0 else year - 1
        semester = "V" if semester == "H" else "H"
        results.append(f"{semester}{str(year).zfill(2)}")

    return results


def get_semester_date_boundaries_from_shorthand(
    shorthand: str,
) -> Tuple[datetime, datetime]:
    """
    get_semester_date_boundaries_from_shorthand takes a semester-year shorthand string,
    e.g. "H18", and returns the date boundaries of the semester.

    This method assumes year values less than 90 refer to the twentyfirst century, and values
    greater than 90 refer to the twentieth century.

    Example:
        shorthand = H18
        result: datetime(2018, 7, 1), datetime(2019, 1, 1)

        shorthand = V99
        result: datetime(1999, 7, 1), datetime(2000, 1, 1)

    :param shorthand:
    :return:
    """
    if not is_valid_semester_year_shorthand(shorthand):
        raise ValueError(
            "Input to get_semester_date_boundaries_from_shorthand not a proper "
            "semester-year shorthand string."
        )

    semester, year = shorthand[0], int(shorthand[1:])

    if year > 90:
        year += 1900
    else:
        year += 2000

    # Get tzinfo
    tzinfo = timezone.now().tzinfo

    return (
        timezone.datetime(
            year=year, month=1 if semester == "V" else 7, day=1, tzinfo=tzinfo
        ),
        timezone.datetime(
            year=year + 1 if semester == "H" else year,
            month=1 if semester == "H" else 7,
            day=1,
            tzinfo=tzinfo,
        ),
    )


def is_valid_semester_year_shorthand(shorthand: str) -> bool:
    """
    is_valid_semester_year_shorthand checks whether or not an input string is a valid
    semester-year shorthand string.

    Examples:
        shorthand = H18
        result: True

        shorthand = H9
        result: False

        shorthand = H09
        result: True

        shorthand: Kebab
        result: False
    :param shorthand:
    :return:
    """
    if len(shorthand) != 3:
        return False

    return re.match(r"[HV]\d{2}", shorthand) is not None


def compress_image(image, max_width, max_height, quality):
    """
    Utility function which compresses image based on parameters such as maximum width and height
    in addition to a quality reduction as a percentage of original image quality.
    :param image: Image to be compressed
    :param max_width: Maximum width of compressed image
    :param max_height: Maximum height of compressed image
    :param quality: Quality reduction in whole number percentage 0-100
    :return InMemoryUploadedFile: Returns compressed image as Django InMemoryUploadedFile object
    """
    temp_image = Image.open(image).convert("RGB")
    temp_image.thumbnail((max_width, max_height))
    output_io_stream = BytesIO()
    temp_image.save(output_io_stream, format="JPEG", quality=quality)
    output_io_stream.seek(0)
    compressed_image = InMemoryUploadedFile(
        output_io_stream,
        "ImageField",
        "%s.jpg" % image.name.split(".")[0],
        "image/jpeg",
        getsizeof(output_io_stream),
        None,
    )
    return compressed_image


def send_email(
    subject="KSG-nett",
    message="",
    html_message="",
    sender="no-reply@ksg-nett.no",
    recipients=[],
    attachments=None,
    cc=[],
    bcc=[],
    fail_silently=True,
) -> bool:
    if len(recipients) + len(bcc) + len(cc) == 0:
        return False

    if not message and html_message:
        message = strip_tags(html_message)

    email = EmailMultiAlternatives(subject, message, sender, recipients, bcc=bcc)

    if html_message:
        email.attach_alternative(html_message, "text/html")

    if attachments:
        if "__iter__" in attachments:
            for attachment in attachments:
                email.attach_file(attachment)
        else:
            email.attach_file(attachments)

    return email.send(fail_silently=fail_silently)


def date_time_combiner(date: datetime.date, time: datetime.time):
    return timezone.make_aware(
        timezone.datetime(
            year=date.year,
            month=date.month,
            day=date.day,
            hour=time.hour,
            minute=time.minute,
            second=time.second,
        )
    )


def get_date_from_datetime(timestamp: timezone.datetime):
    return date(year=timestamp.year, month=timestamp.month, day=timestamp.day)


def parse_datetime_to_midnight(timestamp: timezone.datetime):
    """Accepts a datetime object and returns the same date but at midnight"""
    return timezone.make_aware(
        timezone.datetime(
            year=timestamp.year,
            month=timestamp.month,
            day=timestamp.day,
            hour=0,
            minute=0,
            second=0,
        )
    )


def validate_qs(queryset):
    if not issubclass(QuerySet, queryset.__class__):
        raise ValueError("Positional argument given is not a QuerySet")


def chose_random_element(iterable):
    iterable_length = len(iterable)
    if iterable_length == 0:
        raise ValueError(f"Length of iterable is 0")

    random_number = random.randint(0, iterable_length - 1)
    return iterable[random_number]
