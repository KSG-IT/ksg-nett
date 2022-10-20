import graphene
from django.utils import timezone
from graphene_django import DjangoObjectType, DjangoConnectionField
from graphene_django_cud.mutations import DjangoCreateMutation, DjangoDeleteMutation
from graphene_django_cud.util import disambiguate_id

from common.decorators import gql_has_permissions
from .models import BarTab, BarTabCustomer, BarTabOrder, BarTabProduct, BarTabInvoice
from .utils import (
    normalize_customer_bar_tab_data,
    create_invoices_from_bar_tab_data,
    create_pdfs_from_invoices,
    send_invoice_email,
)


class BarTabCustomerNode(DjangoObjectType):
    class Meta:
        model = BarTabCustomer
        interfaces = (graphene.Node,)

    orders = graphene.List(lambda: BarTabOrderNode)

    def resolve_orders(self: BarTabCustomer, info, **kwargs):
        return self.orders.all()

    @classmethod
    @gql_has_permissions("bar_tab.view_bartabcustomer")
    def get_node(cls, info, id):
        return BarTabCustomer.objects.get(id=id)


class BarTabOrderNode(DjangoObjectType):
    class Meta:
        model = BarTabOrder
        interfaces = (graphene.Node,)

    get_name_display = graphene.String(source="get_name_display")
    purchased_where = graphene.String(source="purchased_where")

    @classmethod
    @gql_has_permissions("bar_tab.view_bartaborder")
    def get_node(cls, info, id):
        return BarTabOrder.objects.get(id=id)


class BarTabNode(DjangoObjectType):
    class Meta:
        model = BarTab
        interfaces = (graphene.Node,)

    orders = graphene.List(BarTabOrderNode)
    invoices = graphene.List(lambda: BarTabInvoiceNode)
    invoices_generated = graphene.Boolean()

    def resolve_orders(self: BarTab, info):
        return self.orders.all().order_by("created_at")

    def resolve_invoices(self: BarTab, info):
        return self.invoices.all()

    def resolve_invoices_generated(self: BarTab, info):
        return not self.invoices.filter(pdf__isnull=True).exists()

    @classmethod
    @gql_has_permissions("bar_tab.view_bartab")
    def get_node(cls, info, id):
        return BarTab.objects.get(id=id)


class BarTabProductNode(DjangoObjectType):
    class Meta:
        model = BarTabProduct
        interfaces = (graphene.Node,)

    @classmethod
    @gql_has_permissions("bar_tab.view_bartabproduct")
    def get_node(cls, info, id):
        return BarTabProduct.objects.get(id=id)


class BarTabInvoiceNode(DjangoObjectType):
    class Meta:
        model = BarTabInvoice
        interfaces = (graphene.Node,)

    pdf = graphene.String()
    email_sent = graphene.Boolean()

    def resolve_pdf(self: BarTabInvoice, info):
        return self.pdf.url if self.pdf else None

    def resolve_email_sent(self: BarTabInvoice, info):
        if self.datetime_sent:
            return True
        return False

    @classmethod
    @gql_has_permissions("bar_tab.view_bartabinvoice")
    def get_node(cls, info, id):
        return BarTabInvoice.objects.get(id=id)


# Rename
class CustomerBarTabSummaryItem(graphene.ObjectType):
    identifying_name = graphene.String()
    total = graphene.Int()


class BarTabCustomerData(graphene.ObjectType):
    customer = graphene.Field(BarTabCustomerNode)
    bar_tab = graphene.Field(BarTabNode)
    orders = graphene.List(BarTabOrderNode)

    summary_data = graphene.List(CustomerBarTabSummaryItem)
    total = graphene.Int()
    we_owe = graphene.Int()
    debt = graphene.Int()


class BarTabQuery(graphene.ObjectType):
    bar_tab = graphene.Node.Field(BarTabNode)
    bar_tab_order = graphene.Node.Field(BarTabOrderNode)
    bar_tab_product = graphene.Node.Field(BarTabProductNode)
    bar_tab_invoice = graphene.Node.Field(BarTabInvoiceNode)
    active_bar_tab = graphene.Field(BarTabNode)

    all_bar_tabs = DjangoConnectionField(BarTabNode)
    all_bar_tab_products = graphene.List(BarTabProductNode)
    all_bar_tab_customers = graphene.List(BarTabCustomerNode)
    bar_tab_customer_data = graphene.List(BarTabCustomerData)

    all_bar_tab_invoices = DjangoConnectionField(BarTabInvoiceNode)

    @gql_has_permissions("bar_tab.view_bartab")
    def resolve_all_bar_tabs(self, info, **kwargs):
        return BarTab.objects.all()

    @gql_has_permissions("bar_tab.view_bartabproduct")
    def resolve_all_bar_tab_products(self, info, **kwargs):
        return BarTabProduct.objects.all().order_by("name")

    @gql_has_permissions("bar_tab.view_bartab")
    def resolve_active_bar_tab(self, info, **kwargs):
        return BarTab.get_active_bar_tab()

    @gql_has_permissions("bar_tab.view_bartabcustomer")
    def resolve_all_bar_tab_customers(self, info, **kwargs):
        return BarTabCustomer.objects.all().order_by("name")

    @gql_has_permissions("bar_tab.view_bartabinvoice")
    def resolve_all_bar_tab_invoices(self, info, **kwargs):
        return BarTabInvoice.objects.all().order_by("-created_at")

    @gql_has_permissions("bar_tab.view_bartabcustomer")
    def resolve_bar_tab_customer_data(self, info, **kwargs):
        """
        Returns a list of BarTabCustomerData objects, which contain the customer, bar tab, and orders
        """

        active_bar_tab = BarTab.get_active_bar_tab()
        customers = BarTabCustomer.objects.filter(
            orders__bar_tab=active_bar_tab
        ).distinct()
        data = normalize_customer_bar_tab_data(active_bar_tab, customers)

        return data


class CreateBarTabMutation(DjangoCreateMutation):
    class Meta:
        model = BarTab
        permissions = ("bar_tab.add_bartab",)
        exclude_fields = ("status",)
        auto_context_fields = {
            "created_by": "user",
        }


class CreateInvoicesMutation(graphene.Mutation):
    invoices = graphene.List(BarTabInvoiceNode)

    @gql_has_permissions("bar_tab.add_bartabinvoice")
    def mutate(self, info):
        active_bar_tab = BarTab.get_active_bar_tab()
        active_bar_tab.invoices.all().delete()
        customers = BarTabCustomer.objects.filter(
            orders__bar_tab=active_bar_tab
        ).distinct()
        data = normalize_customer_bar_tab_data(active_bar_tab, customers)

        invoices = create_invoices_from_bar_tab_data(data, user=info.context.user)
        active_bar_tab.status = active_bar_tab.Status.UNDER_REVIEW
        active_bar_tab.save()
        return CreateInvoicesMutation(invoices=invoices)


class GenerateInvoicePDFsMutation(graphene.Mutation):
    ok = graphene.Boolean()

    @gql_has_permissions("bar_tab.change_bartabinvoice")
    def mutate(self, info):
        active_bar_tab = BarTab.get_active_bar_tab()
        invoices = BarTabInvoice.objects.filter(bar_tab=active_bar_tab)
        invoices.update(pdf=None)
        create_pdfs_from_invoices(invoices)
        return GenerateInvoicePDFsMutation(ok=True)


class DeleteActiveBarTabPDFsMutation(graphene.Mutation):
    ok = graphene.Boolean()

    @gql_has_permissions("bar_tab.change_bartabinvoice")
    def mutate(self, info):
        active_bar_tab = BarTab.get_active_bar_tab()
        # If we have sent an email with the bill too late to delete it
        invoices = BarTabInvoice.objects.filter(
            bar_tab=active_bar_tab, datetime_sent__isnull=True
        )
        invoices.update(pdf=None)
        return DeleteActiveBarTabPDFsMutation(ok=True)


class LockBarTabMutation(graphene.Mutation):
    bar_tab = graphene.Field(BarTabNode)

    @gql_has_permissions("bar_tab.change_bartab")
    def mutate(self, info):
        bar_tab = BarTab.get_active_bar_tab()
        bar_tab.status = BarTab.Status.LOCKED
        bar_tab.closed_by = info.context.user
        bar_tab.datetime_closed = timezone.now()
        bar_tab.save()
        return LockBarTabMutation(bar_tab=bar_tab)


class BarTabUnderReviewMutation(graphene.Mutation):
    bar_tab = graphene.Field(BarTabNode)

    @gql_has_permissions("bar_tab.change_bartab")
    def mutate(self, info):
        bar_tab = BarTab.get_active_bar_tab()
        bar_tab.status = BarTab.Status.UNDER_REVIEW
        bar_tab.save()

        return BarTabUnderReviewMutation(bar_tab=bar_tab)


class CreateBarTabOrderMutation(DjangoCreateMutation):
    class Meta:
        model = BarTabOrder
        permissions = ("bar_tab.add_bartaborder",)
        exclude_fields = ("cost",)

    @classmethod
    def before_mutate(cls, root, info, input):
        quantity = input["quantity"]
        if quantity < 1:
            raise Exception("Quantity must be greater than 0")
        elif quantity > 100:
            raise Exception("Quantity must be less than 100")

        product_id = input["product"]
        product_id = disambiguate_id(product_id)
        product = BarTabProduct.objects.get(id=product_id)
        input["cost"] = product.price * input["quantity"]

        name = input["name"]
        if name != "":
            name = name.strip()
            name = name.lower()
            name_list = name.split(" ")
            name_list = [word.strip() for word in name_list]
            name_list = [word.capitalize() for word in name_list]
            name = " ".join(name_list)
            input["name"] = name

        return input


class DeleteBarTabOrderMutation(DjangoDeleteMutation):
    class Meta:
        model = BarTabOrder
        permissions = ("bar_tab.delete_bartaborder",)

    @classmethod
    def validate(cls, root, info, input):
        id = disambiguate_id(input)
        order = BarTabOrder.objects.get(id=id)

        if order and not order.bar_tab.status == BarTab.Status.OPEN:
            raise ValueError("Closed tabs cannot be modified")

        super().validate(root, info, input)


class SendBarTabInvoiceEmailMutation(graphene.Mutation):
    class Arguments:
        invoice_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @gql_has_permissions("bar_tab.change_bartabinvoice")
    def mutate(self, info, invoice_id):
        invoice_id = disambiguate_id(invoice_id)
        invoice = BarTabInvoice.objects.get(id=invoice_id)
        if not invoice.pdf:
            raise ValueError("Invoice must have a PDF before it can be emailed")

        # Fail silently set to False
        send_invoice_email(invoice, info.context.user)
        invoice.datetime_sent = timezone.now()
        invoice.save()
        return SendBarTabInvoiceEmailMutation(ok=True)


class FinalizeBarTabMutation(graphene.Mutation):

    bar_Tab = graphene.Field(BarTabNode)

    @gql_has_permissions("bar_tab.change_bartabinvoice")
    def mutate(self, info):
        active_bar_tab = BarTab.get_active_bar_tab()
        unsent_invoices = active_bar_tab.invoices.filter(datetime_sent__isnull=True)

        if unsent_invoices.exists():
            raise Exception("Cannot finalize bar tab with unsent invoices")

        active_bar_tab.stats = BarTab.Status.REVIEWED
        active_bar_tab.save()
        return FinalizeBarTabMutation(bar_tab=active_bar_tab)


class BarTabMutations(graphene.ObjectType):
    create_bar_tab = CreateBarTabMutation.Field()
    lock_bar_tab = LockBarTabMutation.Field()
    finalize_bar_tab = FinalizeBarTabMutation.Field()

    create_bar_tab_order = CreateBarTabOrderMutation.Field()
    delete_bar_tab_order = DeleteBarTabOrderMutation.Field()

    # rename these to mention active bar tab as a variable name
    create_invoices = CreateInvoicesMutation.Field()
    generate_pdf = GenerateInvoicePDFsMutation.Field()
    delete_active_bar_tab_pdfs = DeleteActiveBarTabPDFsMutation.Field()
    send_bar_tab_invoice_email = SendBarTabInvoiceEmailMutation.Field()
