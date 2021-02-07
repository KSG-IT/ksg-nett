import random
from factory import Faker, RelatedFactory, sequence, SubFactory
from factory.django import DjangoModelFactory

from organization.models import InternalGroup, Commission, InternalGroupPosition


class InternalGroupFactory(DjangoModelFactory):
    class Meta:
        model = InternalGroup

    name = Faker('text')
    type = random.choices(InternalGroup.Type.choices)[0]
    description = Faker('text')
    members = RelatedFactory('users.tests.factories.UserFactory')


class InternalGroupPositionFactory(DjangoModelFactory):
    class Meta:
        model = InternalGroupPosition

    name = Faker('text')
    internal_group = SubFactory(InternalGroupFactory)


class CommissionFactory(DjangoModelFactory):
    class Meta:
        model = Commission

    name = sequence(lambda n: "Agent %03d" % n)
