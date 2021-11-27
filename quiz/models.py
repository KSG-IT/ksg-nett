from django.db import models
from django.db.models.fields import BooleanField, SmallIntegerField
from django.db.models.fields import related
from django.db.models.fields.related import ManyToManyField
from users.models import User
from random import randint
from model_utils.managers import QueryManager
from quiz.consts import InternalGroups
# Create your models here.

class Quiz(models.Model):
    participants = models.ManyToManyField(User, through='Participant', through_fields=('quiz', 'correct_user'), blank=True, related_name="participants")
    fake_users = models.ManyToManyField(User, related_name="quiz_fakes")

    @property
    def current_user(self):
        not_guessed_yet = self.quiz_choices.filter(appears_in_quiz=self)
        if not not_guessed_yet:
            return None
        return not_guessed_yet.first()

class Participant(models.Model): #QuizAnswer FK -> QUIZ
    guessed_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="clicked_in_quiz", null=True)
    correct_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="solution_in_quiz", null=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)

    @property
    def correct(self):
        return self.guessed_user == self.correct_user

    @property
    def counter(self):
        return self.quiz.related_quiz.filter(guessed_user__isnull=False).count()
        return Participant.objects.filter(quiz=self.quiz, guessed_user__isnull=False).count()


