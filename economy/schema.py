import graphene
from graphene import Node
from django.db.models import Q
from graphene_django import DjangoObjectType
from django.utils import timezone
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django.filter import DjangoFilterConnectionField
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
    amount =graphene.NonNull( graphene.Int)
    quantity =graphene.NonNull(graphene.Int)  # Transfer or deposit either 1 or None
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


class SociBankAccountNode(DjangoObjectType):
    class Meta:
        model = SociBankAccount
        interfaces = (Node,)

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


class DepositNode(DjangoObjectType):
    class Meta:
        model = Deposit
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return Deposit.objects.get(pk=id)


class SociProductQuery(graphene.ObjectType):
    soci_product = Node.Field(SociProductNode)
    all_active_soci_products = DjangoConnectionField(SociProductNode)
    all_soci_products = DjangoConnectionField(SociProductNode)

    def resolve_all_soci_products(self, info, *args, **kwargs):
        return SociProduct.objects.all()

    def resolve_all_active_soci_products(self, info, *args, **kwargs):
        return SociProduct.objects.filter(
            Q(end__isnull=True) | Q(end__gte=timezone.now())
        )


class ProductOrderQuery(graphene.ObjectType):
    product_order = Node.Field(ProductOrderNode)
    all_product_orders = DjangoConnectionField(ProductOrderNode)

    def resolve_all_product_orders(self, info, *args, **kwargs):
        return ProductOrder.objects.all().order_by("created_at")


class SociSessionQuery(graphene.ObjectType):
    soci_session = Node.Field(SociSessionNode)
    all_soci_sessions = DjangoConnectionField(SociSessionNode)

    def resolve_all_soci_sessions(self, info, *args, **kwargs):
        return SociSession.objects.all().order_by("created_at")


class SociBankAccountQuery(graphene.ObjectType):
    soci_bank_account = Node.Field(SociBankAccountNode)
    all_soci_bank_accounts = DjangoConnectionField(SociBankAccountNode)

    def resolve_all_soci_bank_accounts(self, info, *args, **kwargs):
        return SociBankAccount.objects.all()


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
