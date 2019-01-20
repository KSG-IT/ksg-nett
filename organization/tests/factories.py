import random

from factory import DjangoModelFactory, Faker, RelatedFactory

from organization.models import InternalGroup, KSG_INTERNAL_GROUPS


class InternalGroupFactory(DjangoModelFactory):
    class Meta:
        model = InternalGroup

    name = random.choice(KSG_INTERNAL_GROUPS)[0]
    description = Faker('text')
    members = RelatedFactory('users.tests.factories.UserFactory')
