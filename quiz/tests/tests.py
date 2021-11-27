from django.test import TestCase
from quiz.models import Quiz
from users.tests.factories import UserFactory
# Create your tests here.

class TestQuizModel(TestCase):
    def setUp(self):
        self.quiz = Quiz.objects.create()
    pass