from factory import Faker, SubFactory, Sequence, post_generation
from factory.django import DjangoModelFactory
from factory.django import FileField
from users.models import User, UsersHaveMadeOut
from django.contrib.auth.models import Permission
from django.db import models
from typing import Optional


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    # From AbstractUser model
    username = Sequence(lambda n: f"username{n}")
    first_name = Faker("first_name")
    last_name = Faker("last_name")

    # From User model
    date_of_birth = Faker("past_date")
    study = Faker("job")
    profile_image = FileField()
    phone = Faker("phone_number")
    study_address = Faker("address")
    home_town = Faker("address")
    start_ksg = Faker("past_date")
    about_me = Faker("sentence")
    in_relationship = False
    anonymize_in_made_out_map = False

    email = Sequence(lambda n: f"user{n}@example.com")


def _get_permission_from_string(string: str) -> Optional[Permission]:
    try:
        if "." in string:
            app_label, codename = string.split(".")
            return Permission.objects.get(
                content_type__app_label=app_label, codename=codename
            )
        else:
            return Permission.objects.get(codename=string)
    except models.ObjectDoesNotExist:
        return None


class UserWithPermissionsFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = Sequence(lambda n: "permissionsusername%d" % n)

    @post_generation
    def permissions(self: User, create, extracted, **kwargs):
        if not create:
            return

        if not extracted:
            return

        if isinstance(extracted, str):
            permission = _get_permission_from_string(extracted)
            if permission is not None:
                self.user_permissions.add(_get_permission_from_string(extracted))
        elif hasattr(extracted, "__iter__"):
            for permission_string in extracted:
                if not isinstance(permission_string, str):
                    continue

                permission = _get_permission_from_string(permission_string)
                if permission is not None:
                    self.user_permissions.add(permission)
        else:
            raise ValueError(
                "Invalid variable input as permissions, expected string or iterable"
            )


class UsersHaveMadeOutFactory(DjangoModelFactory):
    class Meta:
        model = UsersHaveMadeOut

    user_one = SubFactory(UserFactory)
    user_two = SubFactory(UserFactory)
