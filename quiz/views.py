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
from quiz.consts import InternalGroups


def quiz_main(request):
    # Quiz.objects.all().delete()
    groups = InternalGroup.objects.filter(type=InternalGroup.Type.INTERNAL_GROUP)
    context = {
        "groups": groups,
    }
    return render(request, template_name="quiz/quiz_main.html", context=context)


def user_quiz_pool_helper(quiz, internal_group):
    pool = None
    group = None
    if internal_group == "new-members":
        all_groups = InternalGroup.objects.filter(
            type=InternalGroup.Type.INTERNAL_GROUP
        ).order_by("?")
    else:
        print("IDENTIFIER: ", quiz.identifier)
        all_groups = InternalGroup.objects.filter(slug=internal_group).order_by("?")
    pool = []
    for group in all_groups:
        pool.extend([membership.user for membership in group.active_members])
    return pool


def quiz_new(request, internal_group):
    quiz = Quiz.objects.create()
    quiz.identifier = internal_group.upper()
    pool_setup = user_quiz_pool_helper(quiz, internal_group)
    quiz.fake_users.set(pool_setup)
    # ----------------------- Snippet generates the first participant to guess on
    users_available = quiz.fake_users.all()
    next_to_guess = choice(users_available)
    x = Participant.objects.create(quiz=quiz, correct_user=next_to_guess)
    x.save()
    quiz.save()
    # -----------------------
    quiz.save()
    return redirect("quiz-detail", quiz_id=quiz.id)


def quiz_results(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    all_guesses = quiz.participants_in_quiz.all()
    context = {
        "quiz": quiz,
        "quiz_amount": QUIZ_QUESTION_AMOUNT,
        "correctly_guessed": quiz.score,
        "quiz_participants": all_guesses,
    }
    return render(request, "quiz/quiz_results.html", context=context)


def quiz_detail_view(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    participant_current = quiz.current_guess
    if quiz.counter < QUIZ_QUESTION_AMOUNT:
        context = {
            "quiz": quiz,
            "choice_pool": quiz.scramble_pool,
            "question_amount": QUIZ_QUESTION_AMOUNT,
            "who_to_find": participant_current.correct_user,
        }
        return render(request, "quiz/quiz_detail.html", context=context)
    else:
        participant_current.delete()
        return redirect("quiz-results", quiz_id=quiz_id)


def quiz_check(request, quiz_id, user_id):
    if request.method == "POST":
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        participant_guessed_on = quiz.current_guess
        clicked_user = User.objects.filter(pk=user_id).first()
        participant_guessed_on.guessed_user = clicked_user
        participant_guessed_on.save()
        quiz.next_guess
        quiz.save()
        return redirect("quiz-detail", quiz_id=quiz_id)
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
