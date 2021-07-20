from django.urls import path

from quiz import views

app_name = "quiz"
urlpatterns = [
    path("", views.quiz_main, name="main"),
    path("new/", views.quiz_new),
]
