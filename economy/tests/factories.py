import pytz
from django.utils import timezone
from factory import SubFactory, Faker, Sequence, post_generation
from factory.django import DjangoModelFactory
from factory.django import ImageField

from economy.models import (
    SociBankAccount,
    SociProduct,
    ProductOrder,
    SociSession,
    Transfer,
    Deposit,
    DepositComment,
)
from ksg_nett import settings


class SociBankAccountFactory(DjangoModelFactory):
    class Meta:
        model = SociBankAccount
        django_get_or_create = ("user",)

    user = SubFactory("users.tests.factories.UserFactory")
    balance = 0
    card_uuid = Faker("ean")


class SociProductFactory(DjangoModelFactory):
    class Meta:
        model = SociProduct

    sku_number = Sequence(lambda n: f"sku{n}")
    name = Faker("word")
    price = Faker("random_number", digits=4, fix_len=True)
    description = Faker("sentence")
    icon = "🤖"
    end = Faker("future_datetime", tzinfo=pytz.timezone(settings.TIME_ZONE))


class SociSessionFactory(DjangoModelFactory):
    class Meta:
        model = SociSession

    name = Faker("sentence")
    created_at = Faker("past_datetime", tzinfo=pytz.timezone(settings.TIME_ZONE))
    created_by = SubFactory("users.tests.factories.UserFactory")


class ProductOrderFactory(DjangoModelFactory):
    class Meta:
        model = ProductOrder

    product = SubFactory(SociProductFactory)
    order_size = 1
    cost = Faker("random_number", digits=2, fix_len=True)
    source = SubFactory(SociBankAccountFactory)
    session = SubFactory(SociSessionFactory)
    purchased_at = Faker("date_time", tzinfo=pytz.timezone(settings.TIME_ZONE))


class TransferFactory(DjangoModelFactory):
    class Meta:
        model = Transfer

    source = SubFactory(SociBankAccountFactory)
    destination = SubFactory(SociBankAccountFactory)
    amount = Faker("random_number", digits=4, fix_len=True)
    created_at = Faker("date_time", tzinfo=pytz.timezone(settings.TIME_ZONE))


class DepositFactory(DjangoModelFactory):
    class Meta:
        model = Deposit

    account = SubFactory(SociBankAccountFactory)
    description = Faker("text")
    amount = Faker("random_number", digits=4, fix_len=True)
    receipt = ImageField()
    created_at = Faker("date_time", tzinfo=pytz.timezone(settings.TIME_ZONE))

    approved_by = SubFactory("users.tests.factories.UserFactory")
    approved_at = None

    @post_generation
    def signed_off_time(self, _create, _extracted, **_kwargs):
        if self.approved_by:
            self.approved_at = timezone.now()


class DepositCommentFactory(DjangoModelFactory):
    class Meta:
        model = DepositComment

    deposit = SubFactory(DepositFactory)
    user = SubFactory("users.tests.factories.UserFactory")
    comment = Faker("text")
    created = Faker("date_time", tzinfo=pytz.timezone(settings.TIME_ZONE))
