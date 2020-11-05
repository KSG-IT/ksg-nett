import random

from factory import Faker, RelatedFactory
from factory.django import DjangoModelFactory


from organization.models import InternalGroup


class InternalGroupFactory(DjangoModelFactory):
    class Meta:
        model = InternalGroup

    name = random.choice(list(InternalGroup.STATUS))[0]
    description = Faker('text')
    members = RelatedFactory('users.tests.factories.UserFactory')
