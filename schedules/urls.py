from django.urls import path
from schedules import views

urlpatterns = [
    path("", views.schedules_home, name="schedules_home"),
]
