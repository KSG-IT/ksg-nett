from datetime import datetime, date
from typing import Union, List

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

