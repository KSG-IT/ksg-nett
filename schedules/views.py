from django.http import HttpResponse
from icalendar import Calendar, Event
from users.models import User
from .models import Shift


def get_schedule_from_ical_token(request, ical_token):
    cal = Calendar()
    user = User.objects.filter(ical_token=ical_token).first()
    if not user:
        return HttpResponse(cal.to_ical(), content_type="text/calendar")

    user_shifts = Shift.objects.filter(slots__user=user)

    for shift in user_shifts:
        event = Event()
        event.add("summary", shift.name)
        event.add("dtstart", shift.datetime_start)
        event.add("dtend", shift.datetime_end)
        event.add("location", shift.location)
        cal.add_component(event)

    interviews = user.interviews_attended.all()
    for interview in interviews:
        event = Event()
        event.add("dtstart", interview.interview_start)
        event.add("dtend", interview.interview_end)
        event.add("location", interview.location.name)

        if hasattr(interview, "applicant"):
            event.add("summary", f"Intervju: {interview.applicant.get_full_name}")
        else:
            event.add("summary", "Tomt intervju")

        for interviewer in interview.interviewers.all().exclude(id=user.id):
            event.add("attendee", interviewer.email)

        cal.add_component(event)

    return HttpResponse(cal.to_ical(), content_type="text/calendar")
