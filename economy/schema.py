import datetime

import graphene
import calendar
from graphene import Node
from django.db.models import Q, F, Sum
from django.db.models.functions import Coalesce
from graphene_django import DjangoObjectType
from django.utils import timezone
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django import DjangoConnectionField
from economy.models import (
    SociProduct,
    Deposit,
    Transfer,
    SociSession,
    SociBankAccount,
    ProductOrder,
)


class BankAccountActivity(graphene.ObjectType):
    # Either name of product, 'Transfer' or 'Deposit' (Should we have a pending deposit status)
    name = graphene.NonNull(graphene.String)
    amount = graphene.NonNull(graphene.Int)
    quantity = graphene.Int()  # Transfer or deposit returns None for this field
    timestamp = graphene.NonNull(graphene.DateTime)


class SociProductNode(DjangoObjectType):
    class Meta:
        model = SociProduct
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return SociProduct.objects.get(pk=id)


class SociSessionNode(DjangoObjectType):
    class Meta:
        model = SociSession
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return SociSession.objects.get(pk=id)


class DepositNode(DjangoObjectType):
    class Meta:
        model = Deposit
        interfaces = (Node,)

    approved = graphene.Boolean(source="approved")

    @classmethod
    def get_node(cls, info, id):
        return Deposit.objects.get(pk=id)


class SociBankAccountNode(DjangoObjectType):
    class Meta:
        model = SociBankAccount
        interfaces = (Node,)

    deposits = graphene.NonNull(graphene.List(graphene.NonNull(DepositNode)))
    last_deposits = graphene.NonNull(graphene.List(graphene.NonNull(DepositNode)))

    def resolve_deposits(self: SociBankAccount, info, **kwargs):
        return self.deposits.all().order_by("-created_at")

    def resolve_last_deposits(self: SociBankAccount, info, **kwargs):
        return self.deposits.all().order_by("-created_at")[:10]

    @classmethod
    def get_node(cls, info, id):
        return SociBankAccount.objects.get(pk=id)


class ProductOrderNode(DjangoObjectType):
    class Meta:
        model = ProductOrder
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return ProductOrder.objects.get(pk=id)


class TransferNode(DjangoObjectType):
    class Meta:
        model = Transfer
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return Transfer.objects.get(pk=id)


class SociProductQuery(graphene.ObjectType):
    soci_product = Node.Field(SociProductNode)
    all_active_soci_products = DjangoConnectionField(SociProductNode)
    all_soci_products = DjangoConnectionField(SociProductNode)

    def resolve_all_soci_products(self, info, *args, **kwargs):
        return SociProduct.objects.all().order_by()

    def resolve_all_active_soci_products(self, info, *args, **kwargs):
        return SociProduct.objects.filter(
            Q(end__isnull=True) | Q(end__gte=timezone.now())
        )


class DepositQuery(graphene.ObjectType):
    deposit = Node.Field(DepositNode)
    all_deposits = DjangoConnectionField(DepositNode)
    all_pending_deposits = graphene.List(
        DepositNode
    )  # Pending will never be more than a couple at a time
    all_approved_deposits = DjangoConnectionField(DepositNode)

    def resolve_all_deposits(self, info, *args, **kwargs):
        return Deposit.objects.all().order_by("-created_at")

    def resolve_all_pending_deposits(self, info, *args, **kwargs):
        return Deposit.objects.filter(signed_off_by__isnull=True).order_by(
            "-created_at"
        )

    def resolve_all_approved_deposits(self, info, *args, **kwargs):
        return Deposit.objects.filter(signed_off_by__isnull=False).order_by(
            "-created_at"
        )


class ProductOrderQuery(graphene.ObjectType):
    product_order = Node.Field(ProductOrderNode)
    all_product_orders = DjangoConnectionField(ProductOrderNode)

    def resolve_all_product_orders(self, info, *args, **kwargs):
        return ProductOrder.objects.all().order_by("-purchased_at")


class SociSessionQuery(graphene.ObjectType):
    soci_session = Node.Field(SociSessionNode)
    all_soci_sessions = DjangoConnectionField(SociSessionNode)

    def resolve_all_soci_sessions(self, info, *args, **kwargs):
        return SociSession.objects.all().order_by("created_at")


class ExpenditureDay(graphene.ObjectType):
    day = graphene.Date()
    sum = graphene.Int()


class TotalExpenditure(graphene.ObjectType):
    data = graphene.List(ExpenditureDay)
    total = graphene.Int()


class TotalExpenditureDateRange(graphene.Enum):
    THIS_MONTH = "this-month"
    THIS_SEMESTER = "this-semester"
    ALL_SEMESTERS = "all-semesters"
    ALL_TIME = "all-time"


class SociBankAccountQuery(graphene.ObjectType):
    soci_bank_account = Node.Field(SociBankAccountNode)
    all_soci_bank_accounts = DjangoConnectionField(SociBankAccountNode)
    my_bank_account = graphene.Field(graphene.NonNull(SociBankAccountNode))
    my_expenditures = graphene.Field(
        TotalExpenditure, date_range=TotalExpenditureDateRange()
    )

    def resolve_my_bank_account(self, info, *args, **kwargs):
        if not hasattr(info.context, "user") or not info.context.user.is_authenticated:
            return None
        return info.context.user.bank_account

    def resolve_all_soci_bank_accounts(self, info, *args, **kwargs):
        return SociBankAccount.objects.all()

    def resolve_my_expenditures(self, info, date_range, *args, **kwargs):
        data = []
        total = 0

        my_bank_account = info.context.user.bank_account

        cal = calendar.Calendar()
        today = datetime.date.today()
        iterator = cal.itermonthdates(today.year, today.month)
        for day in iterator:
            # Won't be any more data in the future
            if day > today:
                data.append(ExpenditureDay(day=day, sum=0))
                continue

            # The iterator returns days in prev month if they are contained in within the first week
            if day.month != today.month:
                continue

            # Create a day datetime range for each day
            day_min = timezone.make_aware(
                timezone.datetime(
                    year=day.year,
                    month=day.month,
                    day=day.day,
                    hour=0,
                    minute=0,
                    second=0,
                )
            )
            day_max = day_min + timezone.timedelta(hours=23, minutes=59, seconds=59)
            # https://blog.zdsmith.com/posts/comparing-dates-and-datetimes-in-the-django-orm.html

            purchases = my_bank_account.product_orders.filter(
                purchased_at__range=(day_min, day_max)
            )
            purchase_sum = purchases.aggregate(
                purchase_sum=Coalesce(Sum(F("order_size") * F("product__price")), 0)
            )["purchase_sum"]
            expenditure_day = ExpenditureDay(day=day, sum=purchase_sum)
            total += purchase_sum
            data.append(expenditure_day)

        return TotalExpenditure(data=data, total=total)


class CreateSociProductMutation(DjangoCreateMutation):
    class Meta:
        model = SociProduct


class PatchSociProductMutation(DjangoPatchMutation):
    class Meta:
        model = SociProduct


class DeleteSociProductMutation(DjangoDeleteMutation):
    class Meta:
        model = SociProduct


class CreateProductOrderMutation(DjangoCreateMutation):
    class Meta:
        model = ProductOrder


class PatchProductOrderMutation(DjangoPatchMutation):
    class Meta:
        model = ProductOrder


class DeleteProductOrderMutation(DjangoDeleteMutation):
    class Meta:
        model = ProductOrder


class CreateSociSessionMutation(DjangoDeleteMutation):
    class Meta:
        model = SociSession


class PatchSociSessionMutation(DjangoPatchMutation):
    class Meta:
        model = SociSession


class DeleteSociSessionMutation(DjangoDeleteMutation):
    class Meta:
        model = SociSession


class CreateSociBankAccountMutation(DjangoCreateMutation):
    class Meta:
        model = SociBankAccount


class PatchSociBankAccountMutation(DjangoPatchMutation):
    class Meta:
        model = SociBankAccount


class CreateDepositMutation(DjangoCreateMutation):
    class Meta:
        model = Deposit

    @classmethod
    def before_save(cls, root, info, input, obj):
        obj.account = info.context.user.bank_account
        return obj


class PatchDepositMutation(DjangoPatchMutation):
    class Meta:
        model = Deposit

    @classmethod
    def before_save(cls, root, info, input, id, obj: Deposit):
        if not obj.signed_off_by:
            obj.account.remove_funds(obj.amount)
            obj.signed_off_time = None
        else:
            obj.account.add_funds(obj.amount)
            obj.signed_off_time = timezone.now()
        return obj


class DeleteDepositMutation(DjangoDeleteMutation):
    class Meta:
        model = Deposit


class EconomyMutations(graphene.ObjectType):
    create_soci_product = CreateSociProductMutation.Field()
    patch_soci_product = PatchSociProductMutation.Field()
    delete_soci_product = DeleteSociProductMutation.Field()

    create_product_order = CreateProductOrderMutation.Field()
    patch_product_order = PatchProductOrderMutation.Field()
    delete_product_order = DeleteProductOrderMutation.Field()

    create_soci_session = CreateSociSessionMutation.Field()
    patch_soci_session = PatchSociSessionMutation.Field()
    delete_soci_session = DeleteSociSessionMutation.Field()

    create_soci_bank_account = CreateSociBankAccountMutation.Field()
    patch_soci_bank_account = PatchSociBankAccountMutation.Field()

    create_deposit = CreateDepositMutation.Field()
    patch_deposit = PatchDepositMutation.Field()
    delete_deposit = DeleteDepositMutation.Field()
