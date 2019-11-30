from factory import DjangoModelFactory, sequence
from commissions.models import Commission


class CommissionFactory(DjangoModelFactory):
    class Meta:
        model = Commission

    name = sequence(lambda n: "Agent %03d" % n)
