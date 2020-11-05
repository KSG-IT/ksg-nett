import pytz
from django.utils import timezone
from factory import SubFactory, Faker, Sequence, post_generation
from factory.django import DjangoModelFactory
from factory.django import ImageField

from economy.models import SociBankAccount, SociProduct, ProductOrder, Purchase, SociSession, Transfer, Deposit, \
    DepositComment
from ksg_nett import settings
from users.tests.factories import UserFactory


class SociBankAccountFactory(DjangoModelFactory):
    class Meta:
        model = SociBankAccount
        django_get_or_create = ("user",)

    user = SubFactory(UserFactory)
    balance = 0
    card_uuid = Faker('ean')


class SociProductFactory(DjangoModelFactory):
    class Meta:
        model = SociProduct

    sku_number = Sequence(lambda n: f"sku{n}")
    name = Faker('word')
    price = Faker('random_number', digits=4, fix_len=True)
    description = Faker('sentence')
    icon = "🤖"
    end = Faker('future_datetime', tzinfo=pytz.timezone(settings.TIME_ZONE))


class SociSessionFactory(DjangoModelFactory):
    class Meta:
        model = SociSession

    name = Faker('sentence')
    start = Faker('past_datetime', tzinfo=pytz.timezone(settings.TIME_ZONE))
    signed_off_by = SubFactory(UserFactory)


class PurchaseFactory(DjangoModelFactory):
    class Meta:
        model = Purchase

    source = SubFactory(SociBankAccountFactory)
    session = SubFactory(SociSessionFactory)


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
    signed_off_time = None

    @post_generation
    def signed_off_time(self, _create, _extracted, **_kwargs):
        if self.signed_off_by:
            self.signed_off_time = timezone.now()


class DepositCommentFactory(DjangoModelFactory):
    class Meta:
        model = DepositComment

    deposit = SubFactory(DepositFactory)
    user = SubFactory('users.tests.factories.UserFactory')
    comment = Faker('text')
