import random

from factory import DjangoModelFactory, Faker, SubFactory
from factory.django import FileField

from users.models import User, UsersHaveMadeOut, KSG_STATUS_TYPES, KSG_ROLES


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    # From AbstractUser model
    username = Faker('user_name')
    first_name = Faker('first_name')
    last_name = Faker('last_name')

    # From User model
    email = Faker('email')
    date_of_birth = Faker('past_date')
    study = Faker('job')
    profile_image = FileField()
    phone = Faker('phone_number')
    study_address = Faker('address')
    home_address = Faker('address')
    start_ksg = Faker('past_date')
    ksg_status = random.choice(KSG_STATUS_TYPES)[0]
    ksg_role = random.choice(KSG_ROLES)[0]
    biography = Faker('sentence')
    in_relationship = False
    anonymize_in_made_out_map = False


class UsersHaveMadeOutFactory(DjangoModelFactory):
    class Meta:
        model = UsersHaveMadeOut

    user_one = SubFactory(UserFactory)
    user_two = SubFactory(UserFactory)
