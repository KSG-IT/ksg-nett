import re
from datetime import datetime, date
from typing import Union, List, Tuple

from django.utils import timezone


def get_semester_year_shorthand(timestamp: Union[datetime, date]) -> str:
    """
    get_semester_year_shortand renders the `timestamp` attribute into a "semester-year"-representation.
    Examples:
        2018-01-01 => V18
        2014-08-30 => H14
        2012-12-30 => H12
    :return: The "semeter-year" display of the `timestamp` attribute.
    """
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
    target_semester, target_year = target_semester_shorthand[0], int(target_semester_shorthand[1:])

    if timestamp.year > now.year or (timestamp.year == now.year and target_semester < semester):  # H < V alphabetically, and hence in the comparison
        return []

    results = [current_semester_shorthand]
    while semester != target_semester or year != target_year:
        year = year if semester == "H" else 99 if year == 0 else year - 1
        semester = "V" if semester == "H" else "H"
        results.append(
            f"{semester}{str(year).zfill(2)}"
        )

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
        results.append(
            f"{semester}{str(year).zfill(2)}"
        )

    return results


def get_semester_date_boundaries_from_shorthand(shorthand: str) -> Tuple[datetime, datetime]:
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
        raise ValueError("Input to get_semester_date_boundaries_from_shorthand not a proper "
                         "semester-year shorthand string.")

    semester, year = shorthand[0], int(shorthand[1:])

    if year > 90:
        year += 1900
    else:
        year += 2000

    # Get tzinfo
    tzinfo = timezone.now().tzinfo

    return (
        timezone.datetime(
            year=year,
            month=1 if semester == "V" else 7,
            day=1,
            tzinfo=tzinfo
        ),
        timezone.datetime(
            year=year+1 if semester == "H" else year,
            month=1 if semester == "H" else 7,
            day=1,
            tzinfo=tzinfo
        )
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

    return re.match(r'[HV]\d{2}', shorthand) is not None
