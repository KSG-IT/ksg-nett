from django.urls import path
from schedules import views

urlpatterns = [
    path("<str:ical_token>", views.get_schedule_from_ical_token, name="schedules"),
]
