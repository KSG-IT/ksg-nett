from django.http import HttpResponse
from icalendar import Calendar, Event
from users.models import User
from .models import Shift


def get_schedule_from_ical_token(request, ical_token):
    user = User.objects.get(ical_token=ical_token)
    user_shifts = Shift.objects.filter(slots__user=user)
    cal = Calendar()

    for shift in user_shifts:
        event = Event()
        event.add("summary", shift.name)
        event.add("dtstart", shift.datetime_start)
        event.add("dtend", shift.datetime_end)
        event.add("location", shift.location)
        cal.add_component(event)
    return HttpResponse(cal.to_ical(), content_type="text/calendar")
