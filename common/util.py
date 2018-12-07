from datetime import datetime, date
from typing import Union


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
