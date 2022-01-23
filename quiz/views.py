from django.contrib.auth.decorators import login_required
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
from quiz.utils import (
    make_a_guess,
    end_quiz,
    generate_fake_users_pool,
    count_score,
    most_correct_clicks,
)
from django.utils import timezone


def quiz_main(request):
    groups = InternalGroup.objects.filter(type=InternalGroup.Type.INTERNAL_GROUP)
    context = {
        "groups": groups,
    }
    return render(request, template_name="quiz/quiz_main.html", context=context)


def quiz_new(request, internal_group):

    quiz = Quiz.objects.create(user_quizzed=request.user, time_started=timezone.now())
    generate_fake_users_pool(quiz, internal_group)
    quiz.create_participant
    return redirect("quiz-detail", quiz_id=quiz.id)


def quiz_results(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    print(count_score())
    print(quiz.get_time_diff)
    context = {
        "quiz": quiz,
        "quiz_amount": QUIZ_QUESTION_AMOUNT,
        "correctly_guessed": quiz.score,
        "quiz_participants": quiz.all_guesses,
        "quiz_time_taken": round(quiz.get_time_diff, 2),
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
        print(f"Saving the score {quiz.score=}")
        end_quiz(quiz)
        return redirect("quiz-results", quiz_id=quiz_id)


@login_required
def quiz_check(request, quiz_id, user_id):
    if request.method == "POST":
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        make_a_guess(quiz, user_id)
        quiz.next_guess
        quiz.save()
        return redirect("quiz-detail", quiz_id=quiz_id)
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)


def quiz_high(request):
    score_list = count_score()
    correctly_clicked = most_correct_clicks()
    context = {
        "score": score_list,
        "guess_rate": correctly_clicked
        # "score_points": score_points,
        # "score_time": score_time,
    }
    return render(request, "quiz/quiz_high.html", context=context)
