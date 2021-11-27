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
    quiz_choices = models.ManyToManyField(User, through='Participant', through_fields=('quiz','correct_user', 'guessed_user'),blank=True, related_name='appears_in_quiz')
    quiz_pick = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pick')
    quiz_question = models.ForeignKey(User, blank=True, on_delete=models.SET_NULL, null=True, related_name='answer')
    #quiz_correct = models.IntegerField(default=0)
    #quiz_progress = models.IntegerField(default=1)
    #user
    identifier = models.CharField(max_length=20, choices=InternalGroups.choices, null=True, blank=True)

    @property
    def current_user(self):
        not_guessed_yet = self.quiz_choices.filter(appears_in_quiz=self)
        if not not_guessed_yet:
            return None
        return not_guessed_yet.first()


class Participant(models.Model): #QuizAnswer FK -> QUIZ
    guessed_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="clicked_in_quiz", null=True)
    correct_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="solution_in_quiz", null=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="related_quiz")
    guessed = models.BooleanField(default=False)
    #guessed_correctly = models.BooleanField(null=True, default=None)


    @property
    def correct(self):
        return self.guessed_user.id == self.correct_user.id

    @property
    def counter(self):
       return Participant.objects.filter(quiz=self.quiz, guessed_user__isnull=False).count()


