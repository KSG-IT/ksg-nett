from django.urls import path

from quiz import views

app_name = "quiz"
urlpatterns = [
    path("", views.quiz_main, name="main"),
    path("<int:quiz_id>/"),
    path("<int:quiz_id>/guess-user/<int:user_id>"),
    path("new/", views.quiz_new),
]
