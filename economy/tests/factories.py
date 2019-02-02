import pytz
from django.utils import timezone
from factory import DjangoModelFactory, SubFactory, Faker, sequence, Sequence
from factory.django import ImageField

from economy.models import SociBankAccount, SociProduct, ProductOrder, Purchase, PurchaseCollection, Transfer, Deposit, \
    DepositComment
from ksg_nett import settings


class SociBankAccountFactory(DjangoModelFactory):
    class Meta:
        model = SociBankAccount

    user = SubFactory('users.tests.factories.UserFactory')
    balance = 0
    display_balance_at_soci = False

    @sequence
    def card_uuid(n):
        fake_number = Faker('ean13').evaluate(None, None, {})
        return fake_number[9:] + str(n)


class SociProductFactory(DjangoModelFactory):
    class Meta:
        model = SociProduct

    sku_number = Sequence(lambda n: Faker('ean13').evaluate(None, None, {}) + str(n))
    name = Faker('word')
    price = Faker('random_number', digits=4, fix_len=True)
    description = Faker('sentence')
    icon = Faker('word')
    expiry_date = Faker('future_datetime', tzinfo=pytz.timezone(settings.TIME_ZONE))


class PurchaseCollectionFactory(DjangoModelFactory):
    class Meta:
        model = PurchaseCollection

    name = Faker('sentence')
    start_period = Faker('past_datetime', tzinfo=pytz.timezone(settings.TIME_ZONE))
    end_period = timezone.now()


class PurchaseFactory(DjangoModelFactory):
    class Meta:
        model = Purchase

    source = SubFactory(SociBankAccountFactory)
    signed_off_by = SubFactory('users.tests.factories.UserFactory')
    collection = SubFactory(PurchaseCollectionFactory)


class ProductOrderFactory(DjangoModelFactory):
    class Meta:
        model = ProductOrder

    product = SubFactory(SociProductFactory)
    order_size = 1
    amount = Faker('random_number', digits=4, fix_len=True)
    purchase = SubFactory(PurchaseFactory)


class TransferFactory(DjangoModelFactory):
    class Meta:
        model = Transfer

    source = SubFactory(SociBankAccountFactory)
    destination = SubFactory(SociBankAccountFactory)
    amount = Faker('random_number', digits=4, fix_len=True)


class DepositFactory(DjangoModelFactory):
    class Meta:
        model = Deposit

    account = SubFactory(SociBankAccountFactory)
    description = Faker('text')
    amount = Faker('random_number', digits=4, fix_len=True)
    receipt = ImageField()

    signed_off_by = SubFactory('users.tests.factories.UserFactory')


class DepositCommentFactory(DjangoModelFactory):
    class Meta:
        model = DepositComment

    deposit = SubFactory(DepositFactory)
    user = SubFactory('users.tests.factories.UserFactory')
    comment = Faker('text')
