from django.db.models.fields import SlugField
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from rest_framework import viewsets, status
from django.template import loader
from django.contrib.auth import get_user_model
from ksg_nett.settings import QUIZ_QUESTION_AMOUNT
from users.models import User
from random import choice, sample, shuffle, random
from quiz.models import Participant, Quiz
from django.urls import reverse
from organization.models import InternalGroup
from quiz.utils import guess_helper, user_quiz_pool_helper


def quiz_main(request):
    groups = InternalGroup.objects.filter(type=InternalGroup.Type.INTERNAL_GROUP)
    context = {
        "groups": groups,
    }
    return render(request, template_name="quiz/quiz_main.html", context=context)



def quiz_new(request, internal_group):
    quiz = Quiz.objects.create()
    quiz.fake_users.set(user_quiz_pool_helper(quiz,internal_group))
    quiz.create_participant
    quiz.save()
    return redirect("quiz-detail", quiz_id=quiz.id)


def quiz_results(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    context = {
        "quiz": quiz,
        "quiz_amount": QUIZ_QUESTION_AMOUNT,
        "correctly_guessed": quiz.score,
        "quiz_participants": quiz.all_guesses,
    }
    return render(request, "quiz/quiz_results.html", context=context)


def quiz_detail_view(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    if quiz.counter < QUIZ_QUESTION_AMOUNT:
        context = {
            "quiz": quiz,
            "choice_pool": quiz.scramble_pool,
            "question_amount": QUIZ_QUESTION_AMOUNT,
            "who_to_find": quiz.current_guess.correct_user,
        }
        return render(request, "quiz/quiz_detail.html", context=context)
    else:
        quiz.current_guess.delete() #delete participant from previous 'quiz_check'
        return redirect("quiz-results", quiz_id=quiz_id)


def quiz_check(request, quiz_id, user_id):
    if request.method == "POST":
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        guess_helper(quiz, user_id)
        quiz.next_guess
        quiz.save()
        return redirect("quiz-detail", quiz_id=quiz_id)
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
