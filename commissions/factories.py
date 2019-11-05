from factory import DjangoModelFactory, Faker
from commissions.models import Commission


class CommissionFactory(DjangoModelFactory):
    class Meta:
        model = Commission

    name = Faker("name")
