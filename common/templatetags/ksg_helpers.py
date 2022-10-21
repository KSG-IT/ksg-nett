from datetime import datetime, date

from django import template

from common.util import get_semester_year_shorthand

register = template.Library()


@register.filter(name="get_semester_year_shorthand", is_safe=True)
def get_semester_year_shorthand_filter(timestamp: datetime) -> str:
    # We raise a violation here, to make authors of the frontend explicitly aware of their mistake
    if not isinstance(timestamp, datetime) and not isinstance(timestamp, date):
        raise ValueError(
            f"Invalid input to get_semester_year_shorthand_filter. "
            f"Expected datetime, got {type(timestamp)}"
        )
    return get_semester_year_shorthand(timestamp)


@register.filter
def format_to_comma(value):
    return value.replace(".", ",")
