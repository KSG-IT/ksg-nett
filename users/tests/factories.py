import random

from factory import DjangoModelFactory, Faker, SubFactory, sequence, Sequence
from factory.django import FileField
from commissions.factories import CommissionFactory
from users.models import User, UsersHaveMadeOut, KSG_STATUS_TYPES, KSG_ROLES


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    # From AbstractUser model
    username = Sequence(lambda n: Faker('user_name').evaluate(None, None, {}) + str(n))
    first_name = Faker('first_name')
    last_name = Faker('last_name')

    # From User model
    date_of_birth = Faker('past_date')
    study = Faker('job')
    profile_image = FileField()
    phone = Faker('phone_number')
    study_address = Faker('address')
    home_address = Faker('address')
    start_ksg = Faker('past_date')
    ksg_status = random.choice(list(KSG_STATUS_TYPES))[0]
    ksg_role = random.choice(list(KSG_ROLES))[0]
    biography = Faker('sentence')
    in_relationship = False
    commission = SubFactory(CommissionFactory)
    anonymize_in_made_out_map = False

    @sequence
    def email(n):
        first_part, last_part = Faker('email').evaluate(None, None, {}).split('@')
        return first_part + str(n) + '@' + last_part


class UsersHaveMadeOutFactory(DjangoModelFactory):
    class Meta:
        model = UsersHaveMadeOut

    user_one = SubFactory(UserFactory)
    user_two = SubFactory(UserFactory)
