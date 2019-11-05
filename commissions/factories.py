from factory import DjangoModelFactory
from commissions.models import Commission


class CommissionFactory(DjangoModelFactory):
    class Meta:
        model = Commission
