from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from quiz.models import QuizImage
from users.models import User
from random import randint


def quiz_main(request):
    return render(request, "quiz/quiz_main.html")


def quiz_new(request):
    users = User.objects.all()
    random_user = users[randint(0, users.count() - 1)]
    return render(
        request, "quiz/quiz_new.html", {"QuizImage": users, "randomuser": random_user}
    )
