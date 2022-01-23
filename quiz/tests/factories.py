from random import choice
from users.tests.factories import UserFactory
from ksg_nett import settings
from factory import Faker, SubFactory
from factory.django import DjangoModelFactory
from factory import post_generation
from django.utils import timezone

from quiz.models import Quiz, Participant


class QuizFactory(DjangoModelFactory):
    class Meta:
        model = Quiz

    user_quizzed = SubFactory(UserFactory)
    time_started = timezone.now()

    @post_generation
    def fake_users(self, create, extracted):
        if not create:
            return
        if extracted:
            for user in extracted:
                self.fake_users.add(user)
        else:
            self.fake_users.set(UserFactory.create_batch(6))

    @post_generation
    def participants(self, create, extracted):
        if not create:
            return
        if extracted:
            for user in extracted:
                if user not in self.fake_users:
                    self.fake_users.add(user)
                self.participants_in_quiz.create(
                    correct_user=choice(self.fake_users.all())
                )
        else:
            self.create_participant
