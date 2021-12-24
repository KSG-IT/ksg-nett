from django.test import TestCase
from quiz.models import Quiz, Participant
from django.urls import reverse
from django.utils import timezone
from users.tests.factories import UserFactory
from random import choice
from quiz.views import quiz_check, quiz_detail_view
from django.shortcuts import get_object_or_404


# Create your tests here.


class TestQuizModel(TestCase):
    def setUp(self):
        self.correct_user = UserFactory()
        self.logged_in_user = UserFactory()
        self.quiz = Quiz.objects.create(
            user_quizzed=self.logged_in_user,
            time_started=timezone.now(),
        )
        self.quiz.fake_users.set(UserFactory.create_batch(6))
        self.quiz.create_participant
        pass

    def test_create_participant_should_relate_to_quiz(self):
        self.assertEqual(self.quiz.participants_in_quiz.count(), 1)

    def test_clicked_user_set_guessed_user(self):
        clicked_on = choice(self.quiz.fake_users.all())
        participant = self.quiz.current_guess
        participant.guessed_user = clicked_on
        participant.save()

    def test_redirect_if_not_logged_in(self):
        response = self.client.post(
            reverse(
                quiz_check, args=[self.quiz.id, choice(self.quiz.fake_users.all()).id]
            ),
            follow=True,
        )
        self.assertRedirects(response, "/login/")

    def test_click_POST_request(self):
        self.user = UserFactory(username="test")
        self.user.set_password("password")
        self.user.save()
        self.client.login(username="test", password="password")
        self.quiz.id
        random_select = choice(self.quiz.fake_users.all())
        response = self.client.post(
            reverse(quiz_check, args=[self.quiz.id, random_select.id]), follow=True
        )
        self.assertRedirects(response, reverse(quiz_detail_view, args=[self.quiz.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.quiz.participants_in_quiz.first().guessed_user, random_select
        )


"""
Jotting down some notes on various tests:
-There should be a test to see whether there exists more than one participant object with correct_user=true and guessed_user=false at any time,
if such a thing occurs, there should be thrown an exception.
-Test which checks if score is calculated correctly using assertequal
-Test to posting a click which gets interpreted by a helper function (currently "guess_helper" or "test_clicked_user_set_guessed_user")
"""
