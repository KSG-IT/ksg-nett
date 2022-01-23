from django.db import models
from django.db.models.fields import BooleanField, SmallIntegerField
from django.db.models.fields import related
from django.db.models.fields.related import ManyToManyField
from users.models import User
from random import randint
from model_utils.managers import QueryManager
from django.db.models import Q
from random import choice, sample
from django.utils import timezone
from datetime import timedelta

# Create your models here.


class Quiz(models.Model):
    participants = models.ManyToManyField(
        User,
        through="Participant",
        through_fields=("quiz", "correct_user"),
        blank=True,
        related_name="related_quiz",
    )
    fake_users = models.ManyToManyField(User, related_name="quiz_fakes")
    user_quizzed = models.ForeignKey(
        User, related_name="user_taking_quiz", on_delete=models.CASCADE, null=True
    )
    time_started = models.DateTimeField(default=timezone.now)
    time_end = models.DateTimeField(blank=True, null=True)
    final_score = models.IntegerField(blank=True, default=0)

    @property
    def current_guess(self):
        return self.participants_in_quiz.filter(
            correct_user__isnull=False, guessed_user__isnull=True
        ).first()

    @property
    def counter(self):
        return self.participants_in_quiz.filter(guessed_user__isnull=False).count()

    @property
    def score(self):
        score = 0
        for guess in self.participants_in_quiz.all():
            score += 1 if guess.correct else 0
        return score

    @property
    def next_guess(self):
        users_available = self.fake_users.exclude(
            solution_in_quiz__quiz=self, solution_in_quiz__isnull=False
        )
        return self.participants_in_quiz.create(correct_user=choice(users_available))

    @property
    def scramble_pool(self):
        return sample(list(self.fake_users.all()), self.fake_users.count())

    @property
    def create_participant(self):
        self.participants_in_quiz.create(correct_user=choice(self.fake_users.all()))

    @property
    def all_guesses(self):
        return self.participants_in_quiz.all()

    @property
    def get_time_diff(self):
        time_diff = self.time_end - self.time_started
        return time_diff.total_seconds()

    def __str__(self):
        return "User: %s,Quiz: %s" % (self.user_quizzed.get_full_name, self.id)


class Participant(models.Model):  # QuizAnswer FK -> QUIZ
    guessed_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="clicked_in_quiz", null=True
    )
    correct_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="solution_in_quiz", null=True
    )
    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name="participants_in_quiz"
    )

    @property
    def correct(self):
        return self.guessed_user == self.correct_user
