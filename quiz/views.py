from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from quiz.models import QuizImage
from users.models import User
from random import randint


def quiz_main(request):
    return render(request, "quiz/quiz_main.html")


def quiz_detail_view(request, quiz_id):
    """
    This view handles rendering the detail view of a quiz
    there are two states
    - Either a quiz is ongoing
    - Or a quiz is finished

    What we should do in this view is return to templates depending on whether or not it is ongoing
    - If it is finished it should simply show the score and time and say congrats or something
    - If it is ongoing it should show the current question/user we are supposed to guess
        - The selection of users and the user we are supposed to guess should be the same even if we refresh the page
        - This means that for every hit this view gets, if the quiz has not progressed it should get the same name
        to guess and the same pool of people to chose from. In other words - Save the user to guess and the pool in the
        model and simply update them for each guess. We have a nother view which should be triggered on
        "quiz/<quiz-id>/guess-user/<user-id>" and checks if its correct, gets a new name to guess and a new pool
        of people to pick from. Then it should do a "reverse" and render this detail view.
    """

    return render(
        request,  # stuff happens here
    )


def quiz_new(request):
    users = User.objects.all()  # what happens if we have 600 users in the database?
    random_user = users[
        randint(0, users.count() - 1)
    ]  # this will change on each page refresh
    return render(
        request, "quiz/quiz_new.html", {"QuizImage": users, "randomuser": random_user}
    )
