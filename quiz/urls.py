from django.urls import path

from quiz import views

# app_name = 'quiz'
urlpatterns = [
    path("", views.quiz_main),
    path("new/<slug:internal_group>", views.quiz_new),
    path("<int:quiz_id>/", views.quiz_detail_view, name="quiz-detail"),
    path("<int:quiz_id>/guess-user/<int:user_id>", views.quiz_check),
    path("<int:quiz_id>/results/", views.quiz_results, name="quiz-results"),
    path("high", views.quiz_high, name="quiz-high"),
]
