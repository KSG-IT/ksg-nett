import random
from factory import Faker, RelatedFactory, sequence, SubFactory
from factory.django import DjangoModelFactory

from organization.models import (
    InternalGroup,
    InternalGroupPosition,
    InternalGroupPositionMembership,
)


class InternalGroupFactory(DjangoModelFactory):
    class Meta:
        model = InternalGroup

    name = Faker("text")
    type = random.choices(InternalGroup.Type.choices)[0]
    description = Faker("text")
    members = RelatedFactory("users.tests.factories.UserFactory")


class InternalGroupPositionFactory(DjangoModelFactory):
    class Meta:
        model = InternalGroupPosition

    name = Faker("text")
    internal_group = SubFactory(InternalGroupFactory)


class InternalGroupPositionMembershipFactory(DjangoModelFactory):
    class Meta:
        model = InternalGroupPositionMembership
