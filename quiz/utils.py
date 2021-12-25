from django.db.models.fields import SlugField
from django.shortcuts import get_object_or_404
from organization.models import InternalGroup
from users.models import User
from quiz.models import Participant, Quiz
from django.db.models import Count, OuterRef, Subquery, Sum
from django.db.models import (
    DateTimeField,
    ExpressionWrapper,
    F,
    fields,
    Q,
    Case,
    When,
    Value,
)
from django.utils import timezone


def generate_fake_users_pool(quiz, internal_group):
    if internal_group == "new-members":
        category = InternalGroup.objects.filter(
            type=InternalGroup.Type.INTERNAL_GROUP
        ).order_by("?")
    else:
        category = InternalGroup.objects.filter(slug=internal_group).order_by("?")
    pool = []
    for group in category:
        pool.extend([membership.user for membership in group.active_members])
    return quiz.fake_users.set(pool)


def make_a_guess(quiz, guessing_user_id):
    participant = quiz.current_guess
    participant.guessed_user = User.objects.get(pk=guessing_user_id)
    participant.save()


def end_quiz(quiz):
    quiz.time_end = timezone.now()
    quiz.final_score = quiz.score
    quiz.save()
    quiz.current_guess.delete()  # delete participant from previous 'quiz_check'


def count_score():
    time_taken_field = ExpressionWrapper(
        F("time_end") - F("time_started"), output_field=fields.DurationField()
    )
    score_by_time = (
        Quiz.objects.all()
        .annotate(time_taken=time_taken_field)
        .order_by("-final_score", "time_taken")
    )
    return [
        [quiz.user_quizzed, quiz.final_score, round(quiz.time_taken.total_seconds(), 4)]
        for quiz in score_by_time[:10]
    ]


def most_correct_clicks():
    filter_correct_guess = (
        Participant.objects.filter(
            Q(correct_user=OuterRef("pk")) & Q(correct_user=F("guessed_user"))
        )
        .order_by()
        .values("correct_user")
    )
    filter_all_guesses = (
        Participant.objects.filter(Q(correct_user=OuterRef("pk")))
        .order_by()
        .values("correct_user")
    )
    count_correct_guesses = filter_correct_guess.annotate(c=Count("*")).values("c")
    count_guesses = filter_all_guesses.annotate(c=Count("*")).values("c")
    most_correct_clicks = (
        User.objects.annotate(
            correct_clicks_cnt=100
            * Subquery(count_correct_guesses, output_field=fields.DecimalField())
            / Subquery(count_guesses, output_field=fields.DecimalField()),
        )
        .values("first_name", "correct_clicks_cnt")
        .order_by("-correct_clicks_cnt")
    )
    return most_correct_clicks
