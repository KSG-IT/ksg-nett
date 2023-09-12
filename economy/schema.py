import datetime

import graphene
import calendar

import pytz
from django.conf import settings
from django.core.exceptions import (
    SuspiciousOperation,
    PermissionDenied,
    ValidationError,
)
from django.db import transaction
from django.forms import FloatField
from graphene import Node
from django.db.models import (
    Q,
    Sum,
    Count,
    F,
    Avg,
    Subquery,
    OuterRef,
    Value,
    Case,
    When,
    BooleanField,
)
from django.db.models.functions import Coalesce, TruncDay, TruncDate
from graphene_django import DjangoObjectType
from django.utils import timezone
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django import DjangoConnectionField
from graphene_django_cud.util import disambiguate_id
from common.exceptions import IllegalOperation

from api.exceptions import InsufficientFundsException
from common.decorators import (
    gql_has_permissions,
    gql_login_required,
)
from common.util import check_feature_flag
from economy.emails import send_deposit_invalidated_email
from economy.models import (
    SociProduct,
    Deposit,
    Transfer,
    SociSession,
    SociBankAccount,
    ProductOrder,
    SociOrderSession,
    SociOrderSessionOrder,
)
from schedules.models import Schedule
from users.models import User


class ExpenditureDay(graphene.ObjectType):
    day = graphene.Date()
    sum = graphene.Int()


class TotalExpenditure(graphene.ObjectType):
    data = graphene.List(ExpenditureDay)
    total = graphene.Int()


class TotalExpenditureItem(graphene.ObjectType):
    name = graphene.String()
    total = graphene.Int()
    quantity = graphene.Int()
    average = graphene.Float()
    data = graphene.List(ExpenditureDay)


class TotalExpenditureDateRange(graphene.Enum):
    THIS_MONTH = "this-month"
    THIS_SEMESTER = "this-semester"
    ALL_SEMESTERS = "all-semesters"
    ALL_TIME = "all-time"


class BankAccountActivity(graphene.ObjectType):
    # Either name of product, 'Transfer' or 'Deposit' (Should we have a pending deposit status)
    name = graphene.NonNull(graphene.String)
    amount = graphene.Int()
    quantity = graphene.Int()  # Transfer or deposit returns None for this field
    timestamp = graphene.NonNull(graphene.DateTime)


class SociProductNode(DjangoObjectType):
    class Meta:
        model = SociProduct
        interfaces = (Node,)

    is_default = graphene.Boolean()

    def resolve_is_default(self: SociProduct, info, *args, **kwargs):
        return self.default_stilletime_product

    @classmethod
    def get_node(cls, info, id):
        return SociProduct.objects.get(pk=id)


class SociSessionNode(DjangoObjectType):
    class Meta:
        model = SociSession
        interfaces = (Node,)

    money_spent = graphene.Int()
    product_orders = graphene.List("economy.schema.ProductOrderNode")
    closed = graphene.Boolean()
    get_name_display = graphene.String()

    def resolve_money_spent(self: SociSession, info, *args, **kwargs):
        return self.total_revenue

    def resolve_product_orders(self: SociSession, info, *args, **kwargs):
        return (
            self.product_orders.all()
            .prefetch_related("source__user", "product")
            .order_by("-purchased_at")
        )

    def resolve_closed(self: SociSession, info, *args, **kwargs):
        return self.closed_at is not None

    def resolve_get_name_display(self: SociSession, info, *args, **kwargs):
        if self.name:
            return self.name
        return f"{self.get_type_display()}: {self.creation_date.strftime('%d.%m.%Y')}"

    @classmethod
    @gql_has_permissions("economy.view_socisession")
    def get_node(cls, info, id):
        return SociSession.objects.get(pk=id)


class DepositNode(DjangoObjectType):
    class Meta:
        model = Deposit
        interfaces = (Node,)

    receipt = graphene.String()

    def resolve_receipt(self: Deposit, info, *args, **kwargs):
        if self.receipt:
            return self.receipt.url
        else:
            return None

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


class SociOrderSessionOrderNode(DjangoObjectType):
    class Meta:
        model = SociOrderSessionOrder
        interfaces = (Node,)

    @classmethod
    @gql_login_required()
    def get_node(cls, info, id):
        return SociOrderSession.objects.get(pk=id)


class SociOrderSessionNode(DjangoObjectType):
    class Meta:
        model = SociOrderSession
        interfaces = (Node,)

    class StatusEnum(graphene.Enum):
        CREATED = SociOrderSession.Status.CREATED
        FOOD_ORDERING = SociOrderSession.Status.FOOD_ORDERING
        DRINK_ORDERING = SociOrderSession.Status.DRINK_ORDERING
        CLOSED = SociOrderSession.Status.CLOSED

    status = graphene.Field(StatusEnum)

    def resolve_status(self: SociOrderSession, info, *args, **kwargs):
        return self.status

    invited_users = graphene.List("users.schema.UserNode")

    def resolve_invited_users(self: SociOrderSession, info, *args, **kwargs):
        return self.invited_users.all().order_by("first_name", "last_name")

    orders = graphene.List(SociOrderSessionOrderNode)

    def resolve_orders(self: SociOrderSession, info, *args, **kwargs):
        return self.orders.all().order_by("ordered_at")

    food_orders = graphene.List(SociOrderSessionOrderNode)

    def resolve_food_orders(self: SociOrderSession, info, *args, **kwargs):
        return self.orders.filter(product__type=SociProduct.Type.FOOD).order_by(
            "ordered_at"
        )

    drink_orders = graphene.List(SociOrderSessionOrderNode)

    def resolve_drink_orders(self: SociOrderSession, info, *args, **kwargs):
        return self.orders.filter(product__type=SociProduct.Type.DRINK).order_by(
            "ordered_at"
        )

    order_pdf = graphene.String()

    def resolve_order_pdf(self: SociOrderSession, info, *args, **kwargs):
        return self.order_pdf.url if self.order_pdf else None

    @classmethod
    @gql_has_permissions("economy.view_sociordersession")
    def get_node(cls, info, id):
        return SociOrderSession.objects.get(pk=id)


class SociProductQuery(graphene.ObjectType):
    soci_product = Node.Field(SociProductNode)
    all_active_soci_products = DjangoConnectionField(SociProductNode)
    all_soci_products = graphene.List(SociProductNode)
    all_soci_products_with_default = graphene.List(SociProductNode)
    all_soci_sessions = DjangoConnectionField(SociSessionNode)
    default_soci_products = graphene.List(SociProductNode)

    default_soci_order_session_food_products = graphene.List(SociProductNode)
    default_soci_order_session_drink_products = graphene.List(SociProductNode)

    @gql_login_required()
    def resolve_all_soci_products_with_default(self, info, *args, **kwargs):
        return (
            SociProduct.objects.all()
            .order_by("type", "name")
            .annotate(
                is_default=Case(
                    When(default_stilletime_product=True, then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                )
            )
        )

    @gql_login_required()
    def resolve_default_soci_order_session_food_products(self, info, *args, **kwargs):
        return SociProduct.objects.filter(
            default_stilletime_product=True, type=SociProduct.Type.FOOD
        ).order_by("price")

    @gql_login_required()
    def resolve_default_soci_order_session_drink_products(self, info, *args, **kwargs):
        return SociProduct.objects.filter(
            default_stilletime_product=True, type=SociProduct.Type.DRINK
        ).order_by("price")

    @gql_has_permissions("economy.view_sociproduct")
    def resolve_all_soci_products(self, info, *args, **kwargs):
        return SociProduct.objects.all().order_by()

    @gql_has_permissions("economy.view_sociproduct")
    def resolve_all_active_soci_products(self, info, *args, **kwargs):
        return SociProduct.objects.filter(
            Q(end__isnull=True) | Q(end__gte=timezone.now())
        )

    @gql_has_permissions("economy.view_socisession")
    def resolve_all_soci_sessions(self, info, *args, **kwargs):
        return SociSession.objects.all().order_by("-created_at")

    @gql_has_permissions("economy.view_sociproduct")
    def resolve_default_soci_products(self, info, *args, **kwargs):
        return SociProduct.objects.filter(default_stilletime_product=True)


class DepositQuery(graphene.ObjectType):
    deposit = Node.Field(DepositNode)
    all_deposits = DjangoConnectionField(
        DepositNode, q=graphene.String(), unverified_only=graphene.Boolean()
    )
    all_pending_deposits = graphene.List(
        DepositNode
    )  # Pending will never be more than a couple at a time
    all_approved_deposits = DjangoConnectionField(DepositNode)
    ongoing_deposit_intent = graphene.Field(DepositNode)

    @gql_has_permissions("economy.approve_deposit")
    def resolve_all_deposits(self, info, q, unverified_only, *args, **kwargs):
        # ToDo implement user fullname search filtering
        return (
            Deposit.objects.filter(
                account__user__first_name__contains=q,
                approved=not unverified_only,
            )
            .order_by("-created_at")
            .prefetch_related("account__user", "approved_by")
        )

    @gql_has_permissions("economy.approve_deposit")
    def resolve_all_pending_deposits(self, info, *args, **kwargs):
        return Deposit.objects.filter(
            approved=False, deposit_method=Deposit.DepositMethod.BANK_TRANSFER
        ).order_by("-created_at")

    @gql_has_permissions("economy.approve_deposit")
    def resolve_all_approved_deposits(self, info, *args, **kwargs):
        return Deposit.objects.filter(approved=True).order_by("-created_at")

    def resolve_ongoing_deposit_intent(self, info, *args, **kwargs):
        user = info.context.user
        try:
            ongoing_deposit_intent = user.bank_account.deposits.get(
                stripe_payment_intent_status=Deposit.StripePaymentIntentStatusOptions.CREATED,
                approved=False,
                deposit_method=Deposit.DepositMethod.STRIPE,
            )
        except Deposit.DoesNotExist:
            ongoing_deposit_intent = None
        return ongoing_deposit_intent


class ProductOrderQuery(graphene.ObjectType):
    product_order = Node.Field(ProductOrderNode)
    all_product_orders = DjangoConnectionField(ProductOrderNode)
    product_orders_by_item_and_date = graphene.Field(
        TotalExpenditureItem,
        product_id=graphene.ID(),
        date_from=graphene.Date(),
        date_to=graphene.Date(),
    )
    product_orders_by_item_and_date_list = graphene.List(
        TotalExpenditureItem,
        product_ids=graphene.List(graphene.ID),
        date_from=graphene.Date(),
        date_to=graphene.Date(),
    )

    def resolve_all_product_orders(self, info, *args, **kwargs):
        return ProductOrder.objects.all().order_by("-purchased_at")

    def resolve_product_orders_by_item_and_date(
        self, info, product_id, date_from, date_to, *args, **kwargs
    ):
        soci_item = disambiguate_id(product_id)

        date_from = timezone.make_aware(
            datetime.datetime.combine(date_from, datetime.time.min)
        )
        date_to = timezone.make_aware(
            datetime.datetime.combine(date_to, datetime.time.max)
        )

        product = SociProduct.objects.get(id=soci_item)

        product_orders = (
            ProductOrder.objects.filter(
                product_id=soci_item, purchased_at__range=(date_from, date_to)
            )
            .annotate(date=TruncDate("purchased_at"))
            .values("date")
            .annotate(sum=Sum("cost"))
            .order_by("date")
        )
        avg = round(product_orders.aggregate(Avg("sum"))["sum__avg"], 2)
        qty = product_orders.aggregate(sum__qty=Sum("sum") / product.price)["sum__qty"]
        total_expenditure = product_orders.aggregate(Sum("sum"))["sum__sum"]

        return TotalExpenditureItem(
            data=[
                ExpenditureDay(
                    day=product_order["date"],
                    sum=product_order["sum"],
                )
                for product_order in product_orders
            ],
            name=product.name,
            average=avg,
            quantity=qty,
            total=total_expenditure,
        )

    def resolve_product_orders_by_item_and_date_list(
        self, info, product_ids, date_from, date_to, *args, **kwargs
    ):
        total_expenditures = []
        for product_id in product_ids:
            total_expenditure = (
                ProductOrderQuery.resolve_product_orders_by_item_and_date(
                    self,
                    info,
                    product_id=product_id,
                    date_from=date_from,
                    date_to=date_to,
                )
            )
            total_expenditures.append(total_expenditure)
        return total_expenditures


class SociSessionQuery(graphene.ObjectType):
    soci_session = Node.Field(SociSessionNode)
    all_soci_sessions = DjangoConnectionField(SociSessionNode)

    def resolve_all_soci_sessions(self, info, *args, **kwargs):
        SociSession.objects.all().delete()
        return SociSession.objects.all().order_by("created_at")


class SociBankAccountQuery(graphene.ObjectType):
    soci_bank_account = Node.Field(SociBankAccountNode)
    all_soci_bank_accounts = DjangoConnectionField(SociBankAccountNode)
    my_bank_account = graphene.Field(graphene.NonNull(SociBankAccountNode))
    my_expenditures = graphene.Field(
        TotalExpenditure, date_range=TotalExpenditureDateRange()
    )
    my_external_charge_qr_code_url = graphene.String()

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
                ),
                timezone=pytz.timezone(settings.TIME_ZONE),
            )
            day_max = day_min + timezone.timedelta(hours=23, minutes=59, seconds=59)
            # https://blog.zdsmith.com/posts/comparing-dates-and-datetimes-in-the-django-orm.html

            purchases = my_bank_account.product_orders.filter(
                purchased_at__range=(day_min, day_max)
            )
            purchase_sum = purchases.aggregate(purchase_sum=Coalesce(Sum("cost"), 0))[
                "purchase_sum"
            ]
            expenditure_day = ExpenditureDay(day=day, sum=purchase_sum)
            total += purchase_sum
            data.append(expenditure_day)

        return TotalExpenditure(data=data, total=total)

    def resolve_my_external_charge_qr_code_url(self, info, *args, **kwargs):
        account = info.context.user.bank_account
        secret = account.external_charge_secret
        if not secret:
            secret = account.regenerate_external_charge_secret()
        return settings.BASE_URL + f"/economy/external-charge-qr-code/{secret}"


class SociOrderSessionQuery(graphene.ObjectType):
    active_soci_order_session = graphene.Field(SociOrderSessionNode)
    my_session_product_orders = graphene.List(SociOrderSessionOrderNode)
    all_soci_order_session_drink_orders = graphene.List(SociOrderSessionOrderNode)

    def resolve_active_soci_order_session(self, info, *args, **kwargs):
        session = SociOrderSession.get_active_session()
        if not session:
            return None

        user = info.context.user

        # Don't think we actually need this check? Makes it more robust at least
        # If you are invited automatically when you created it shouldn't be an issue
        if session.status == SociOrderSession.Status.CREATED and not user.has_perm(
            "economy.change_sociordersession"
        ):
            return None

        if not session.invited_users.filter(pk=user.pk).exists():
            return None

        return session

    def resolve_my_session_product_orders(self, info, *args, **kwargs):
        status = SociOrderSession.get_active_session().status

        if status == SociOrderSession.Status.FOOD_ORDERING:
            return SociOrderSession.get_active_session().orders.filter(
                user=info.context.user, product__type=SociProduct.Type.FOOD
            )
        elif status == SociOrderSession.Status.DRINK_ORDERING:
            return SociOrderSession.get_active_session().orders.filter(
                user=info.context.user, product__type=SociProduct.Type.DRINK
            )

        return []

    def resolve_all_soci_order_session_drink_orders(self, info, *args, **kwargs):
        me = info.context.user
        session = me.get_invited_soci_order_session

        if not session:
            return None

        return session.orders.filter(product__type=SociProduct.Type.DRINK).order_by(
            "ordered_at"
        )


class StripeQuery(graphene.ObjectType):
    get_client_secret_from_deposit_id = graphene.String(
        deposit_id=graphene.ID(required=True)
    )

    @gql_login_required()
    def resolve_get_client_secret_from_deposit_id(
        self, info, deposit_id, *args, **kwargs
    ):
        import stripe

        deposit_id = disambiguate_id(deposit_id)
        deposit = Deposit.objects.get(id=deposit_id)

        stripe.api_key = settings.STRIPE_SECRET_KEY
        intent = stripe.PaymentIntent.retrieve(deposit.stripe_payment_id)

        return intent.client_secret


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


class UndoProductOrderMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    found = graphene.Boolean()

    @gql_has_permissions("economy.delete_productorder")
    def mutate(self, info, id):
        id = disambiguate_id(id)
        product_order = ProductOrder.objects.get(id=id)
        session = product_order.session
        if session.closed:
            raise SuspiciousOperation("Cannot undo a product order in a closed session")

        if session.type == SociSession.Type.SOCIETETEN:
            raise SuspiciousOperation("Cannot undo a product order in a Soci Session")

        account = product_order.source
        with transaction.atomic():
            account.add_funds(product_order.cost)
            product_order.delete()
        return UndoProductOrderMutation(found=True)


class PlaceProductOrderMutation(graphene.Mutation):
    class Arguments:
        soci_session_id = graphene.ID(required=True)
        user_id = graphene.ID(required=True)
        product_id = graphene.ID(required=True)
        order_size = graphene.Int(required=True)
        overcharge = graphene.Boolean(required=False)

    product_order = graphene.Field(ProductOrderNode)

    @gql_has_permissions("economy.add_productorder")
    def mutate(
        self,
        info,
        soci_session_id,
        user_id,
        product_id,
        order_size,
        overcharge=False,
        *args,
        **kwargs,
    ):
        """
        Overcharging is only allowed if the user has the permission to do so. Overcharging means
        that the user can order more than the amount of money they have in their bank account.
        """

        request_user = info.context.user
        if overcharge and not request_user.has_perm("economy.can_overcharge"):
            # Check this early to simplify rest of business logic
            raise PermissionDenied("You do not have permission to overcharge")

        soci_session_id = disambiguate_id(soci_session_id)
        session = SociSession.objects.get(id=soci_session_id)
        if session.closed:
            raise SuspiciousOperation("Cannot place order on a closed session")

        user_id = disambiguate_id(user_id)
        user = User.objects.get(id=user_id)

        product_id = disambiguate_id(product_id)
        product = SociProduct.objects.get(id=product_id)
        account = user.bank_account
        cost = product.price * order_size

        remaining_balance = account.balance - cost
        can_afford = session.minimum_remaining_balance <= remaining_balance

        if can_afford:
            account.remove_funds(cost)
            product_order = ProductOrder.objects.create(
                source=account,
                product=product,
                order_size=order_size,
                cost=cost,
                session=session,
            )
            return PlaceProductOrderMutation(product_order=product_order)

        # Cannot afford it and overcharge is not allowed
        if not overcharge and not account.is_gold:
            raise InsufficientFundsException("Insufficient funds")

        account.remove_funds(cost)
        product_order = ProductOrder.objects.create(
            source=account,
            product=product,
            order_size=order_size,
            cost=cost,
            session=session,
        )
        return PlaceProductOrderMutation(product_order=product_order)


class CreateSociSessionMutation(DjangoCreateMutation):
    class Meta:
        model = SociSession
        permissions = ("economy.add_socisession",)
        auto_context_fields = {"created_by": "user"}

    def validate_minimum_remaining_balance(root, info, value, input, **kwargs):
        if value < 0:
            raise ValidationError("Minimum remaining balance cannot be negative")
        return value


class PatchSociSessionMutation(DjangoPatchMutation):
    class Meta:
        model = SociSession


class CloseSociSessionMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    soci_session = graphene.Field(SociSessionNode)

    @gql_has_permissions("economy.change_socisession")
    def mutate(self, info, id, *args, **kwargs):
        from economy.utils import stilletime_closed_email_notification

        id = disambiguate_id(id)
        soci_session = SociSession.objects.get(id=id)
        if soci_session.type == SociSession.Type.SOCIETETEN:
            raise SuspiciousOperation(
                f"Cannot close a session of type {SociSession.Type.SOCIETETEN}"
            )

        if soci_session.product_orders.count() == 0:
            soci_session.delete()
            return CloseSociSessionMutation(soci_session=None)

        soci_session.closed_at = timezone.now()
        soci_session.save()
        if soci_session.type == SociSession.Type.STILLETIME:
            stilletime_closed_email_notification(soci_session)
        return CloseSociSessionMutation(soci_session=soci_session)


class DeleteSociSessionMutation(DjangoDeleteMutation):
    class Meta:
        model = SociSession


class PatchSociBankAccountMutation(DjangoPatchMutation):
    class Meta:
        model = SociBankAccount
        exclude_fields = ("balance",)

    @classmethod
    def before_mutate(cls, root, info, input, id):
        user = info.context.user
        id = int(disambiguate_id(id))
        if user.bank_account.id != id and not user.has_perm(
            "economy.change_socibankaccount"
        ):
            raise PermissionError("You do not have permission to change this account")

        return input


class DeleteDepositMutation(DjangoDeleteMutation):
    class Meta:
        model = Deposit

    @classmethod
    def before_save(cls, root, info, input, obj):
        if obj.approved:
            raise Exception("Cannot delete approved deposit")

        user = info.context.user

        has_permission = user.has_perm("economy.delete_deposit")
        is_my_deposit = obj.account = user.bank_account

        if not (has_permission or is_my_deposit):
            raise PermissionError("You do not have permission to delete this deposit")

        if obj.deposit_method == Deposit.DepositMethod.STRIPE and obj.stripe_payment_id:
            import stripe

            stripe.api_key = settings.STRIPE_SECRET_KEY

            stripe.PaymentIntent.cancel(
                obj.stripe_payment_id,
                cancellation_reason="requested_by_customer",
            )

        return obj


class ApproveDepositMutation(graphene.Mutation):
    class Arguments:
        deposit_id = graphene.ID(required=True)
        corrected_amount = graphene.Int()

    deposit = graphene.Field(DepositNode)

    @gql_has_permissions("economy.approve_deposit")
    def mutate(self, info, deposit_id, corrected_amount=None, *args, **kwargs):
        deposit_id = disambiguate_id(deposit_id)
        deposit = Deposit.objects.get(id=deposit_id)

        if deposit.deposit_method == Deposit.DepositMethod.STRIPE:
            raise Exception("Cannot manually approve Stripe deposits")

        if deposit.approved:
            # Already approved. Do nothing
            return ApproveDepositMutation(deposit=deposit)

        from economy.utils import send_deposit_approved_email

        deposit.approved_at = timezone.now()
        deposit.approved_by = info.context.user
        deposit.approved = True

        if corrected_amount:
            deposit.amount = corrected_amount
            deposit.resolved_amount = corrected_amount

        deposit.save()
        deposit.account.add_funds(deposit.amount)
        if deposit.account.user.notify_on_deposit:
            send_deposit_approved_email(deposit)

        return ApproveDepositMutation(deposit=deposit)


class InvalidateDepositMutation(graphene.Mutation):
    class Arguments:
        deposit_id = graphene.ID(required=True)

    deposit = graphene.Field(DepositNode)

    @gql_has_permissions("economy.invalidate_deposit")
    def mutate(self, info, deposit_id):
        deposit_id = disambiguate_id(deposit_id)
        deposit = Deposit.objects.get(id=deposit_id)

        if not deposit.approved:
            # Already invalidated. Do nothing
            return ApproveDepositMutation(deposit=deposit)

        if deposit.deposit_method == Deposit.DepositMethod.STRIPE:
            raise Exception("Cannot manually invalidate Stripe deposits")

        deposit.approved_at = None
        deposit.approved_by = None
        deposit.approved = False
        deposit.save()
        deposit.account.remove_funds(deposit.resolved_amount)
        if deposit.account.user.notify_on_deposit:
            send_deposit_invalidated_email(deposit)

        return InvalidateDepositMutation(deposit=deposit)


class CreateSociOrderSessionMutation(graphene.Mutation):
    class Meta:
        model = SociOrderSession
        permissions = ("economy.add_sociordersession",)
        auto_context_fields = {"created_by": "user"}

    soci_order_session = graphene.Field(SociOrderSessionNode)

    @gql_has_permissions("economy.add_sociordersession")
    def mutate(self, info, *args, **kwargs):
        from economy.utils import send_soci_order_session_invitation_email

        active_session = SociOrderSession.get_active_session()
        if active_session:
            most_recent_purchase = (
                active_session.orders.all().order_by("-ordered_at").first()
            )

            now = timezone.now()
            purchase_time_delta = now - getattr(most_recent_purchase, "ordered_at", now)

            # If most recent order is more than 6 hours ago we can assume they forgot to close the session
            if purchase_time_delta.seconds // 3600 > 6:
                active_session.closed_at = now
                active_session.closed_by = active_session.created_by
                active_session.status = SociOrderSession.Status.CLOSED
                active_session.save()
            else:
                raise IllegalOperation(
                    f"Cannot create a new session while another is active."
                )
        with transaction.atomic():
            soci_session = SociOrderSession.objects.create(
                status=SociOrderSession.Status.FOOD_ORDERING,
                created_by=info.context.user,
            )
            invited_users = Schedule.get_all_users_working_now()
            invited_users_list = list(invited_users)
            invited_users_list.append(info.context.user)
            soci_session.invited_users.add(*invited_users_list)
            # Don't really need to send invited users. They are already part of the session?
            send_soci_order_session_invitation_email(soci_session, invited_users)

            return CreateSociOrderSessionMutation(soci_order_session=soci_session)


class SociOrderSessionNextStatusMutation(graphene.Mutation):
    soci_order_session = graphene.Field(SociOrderSessionNode)

    @gql_has_permissions("economy.change_sociordersession")
    def mutate(self, info, *args, **kwargs):
        soci_order_session = SociOrderSession.get_active_session()

        if not soci_order_session:
            raise SuspiciousOperation("There is no active session")

        if soci_order_session.status == SociOrderSession.Status.CREATED:
            soci_order_session.status = SociOrderSession.Status.FOOD_ORDERING
            soci_order_session.save()
            return SociOrderSessionNextStatusMutation(
                soci_order_session=soci_order_session
            )

        if soci_order_session.status == SociOrderSession.Status.FOOD_ORDERING:
            from economy.utils import create_food_order_pdf_file

            with transaction.atomic():
                orders = soci_order_session.orders.filter(
                    product__type=SociProduct.Type.FOOD
                )
                session = SociSession.objects.create(
                    type=SociSession.Type.BURGERLISTE,
                    created_by=info.context.user,
                )
                for order in orders:
                    price = order.product.price
                    amount = order.amount
                    total = price * amount

                    purchase = ProductOrder.objects.create(
                        session=session,
                        product=order.product,
                        order_size=order.amount,
                        cost=total,
                        source=order.user.bank_account,
                    )
                    purchase.purchased_at = order.ordered_at
                    purchase.save()
                    order.user.bank_account.remove_funds(total)

                session.closed_at = timezone.now()
                session.save()

                soci_order_session.status = SociOrderSession.Status.DRINK_ORDERING
                file = create_food_order_pdf_file(soci_order_session)
                soci_order_session.order_pdf.save("burgerliste.pdf", file)
                soci_order_session.save()

                return SociOrderSessionNextStatusMutation(
                    soci_order_session=soci_order_session
                )

        if soci_order_session.status == SociOrderSession.Status.DRINK_ORDERING:
            with transaction.atomic():
                soci_order_session.status = SociOrderSession.Status.CLOSED
                soci_order_session.closed_at = timezone.now()
                soci_order_session.closed_by = info.context.user
                orders = soci_order_session.orders.filter(
                    product__type=SociProduct.Type.DRINK
                )
                session = SociSession.objects.create(
                    type=SociSession.Type.STILLETIME,
                    created_by=info.context.user,
                )
                session.created_at = soci_order_session.created_at

                for order in orders:
                    # Drink orders are paid when registered. So no need to charge here
                    price = order.product.price
                    amount = order.amount
                    total = price * amount

                    product_order = ProductOrder.objects.create(
                        session=session,
                        product=order.product,
                        order_size=order.amount,
                        cost=total,
                        source=order.user.bank_account,
                    )
                    product_order.purchased_at = order.ordered_at
                    product_order.save()

                soci_order_session.save()
                session.closed_at = timezone.now()
                session.save()
                return SociOrderSessionNextStatusMutation(
                    soci_order_session=soci_order_session
                )


class PlaceSociOrderSessionOrderMutation(graphene.Mutation):
    class Arguments:
        product_id = graphene.ID(required=True)
        amount = graphene.Int(required=True)

    soci_order_session_order = graphene.Field(SociOrderSessionOrderNode)

    @gql_login_required()
    def mutate(self, info, product_id, amount, *args, **kwargs):
        active_session = SociOrderSession.get_active_session()
        product = SociProduct.objects.get(id=disambiguate_id(product_id))

        if (
            active_session.status != SociOrderSession.Status.FOOD_ORDERING
            and product.type == SociProduct.Type.FOOD
        ):
            raise IllegalOperation("The session is not open for food ordering")

        if (
            active_session.status != SociOrderSession.Status.DRINK_ORDERING
            and product.type == SociProduct.Type.DRINK
        ):
            raise IllegalOperation("The session is not open for drink ordering")

        me = info.context.user
        balance = me.bank_account.balance
        cost = product.price * amount

        previous_orders = active_session.orders.filter(
            user=me, product__type=SociProduct.Type.FOOD
        )
        total_cost = sum(
            [order.amount * order.product.price for order in previous_orders]
        )
        total_cost += cost

        if active_session.status == SociOrderSession.Status.FOOD_ORDERING:
            cost_check = total_cost
        else:
            cost_check = cost

        if cost_check > balance and not me.bank_account.is_gold:
            raise IllegalOperation("You do not have enough funds to place this order")

        with transaction.atomic():
            order = SociOrderSessionOrder.objects.create(
                session=active_session,
                product=product,
                amount=amount,
                user=me,
            )
            if active_session.status == SociOrderSession.Status.DRINK_ORDERING:
                # During drink ordering we instantly charge the user
                me.bank_account.remove_funds(cost)

            return PlaceSociOrderSessionOrderMutation(soci_order_session_order=order)


class DeleteSociOrderSessionFoodOrderMutation(graphene.Mutation):
    """
    Only intended to use with food ordering. Should probably be renamed??¿
    """

    class Arguments:
        order_id = graphene.ID(required=True)

    found = graphene.Boolean()

    @gql_login_required()
    def mutate(self, info, order_id, *args, **kwargs):
        active_session = SociOrderSession.get_active_session()
        if active_session.status != SociOrderSession.Status.FOOD_ORDERING:
            raise IllegalOperation("Food ordering is not open, cannot delete entry")

        me = info.context.user
        order = SociOrderSessionOrder.objects.get(id=disambiguate_id(order_id))
        if order.user != info.context.user and not me.has_perm(
            "economy.delete_sociordersessionorder"
        ):
            raise PermissionError(
                "You do not have permission to delete other users orders"
            )

        with transaction.atomic():
            order.delete()
            return DeleteSociOrderSessionFoodOrderMutation(found=True)


class InviteUsersToSociOrderSessionMutation(graphene.Mutation):
    class Arguments:
        users = graphene.List(graphene.ID, required=True)

    soci_order_session = graphene.Field(SociOrderSessionNode)

    @gql_has_permissions("economy.change_sociordersession")
    def mutate(self, info, users, *args, **kwargs):
        from economy.utils import send_soci_order_session_invitation_email

        active_session = SociOrderSession.get_active_session()
        disambiguated_ids = [disambiguate_id(user) for user in users]

        user_qs = User.objects.filter(id__in=disambiguated_ids)
        active_session.invited_users.add(*list(user_qs))
        send_soci_order_session_invitation_email(active_session, user_qs)
        return InviteUsersToSociOrderSessionMutation(soci_order_session=active_session)


class DepositMethodEnum(graphene.Enum):
    STRIPE = Deposit.DepositMethod.STRIPE
    BANK_TRANSFER = Deposit.DepositMethod.BANK_TRANSFER


class CreateDepositMutation(graphene.Mutation):
    class Arguments:
        amount = graphene.Int(required=True)
        description = graphene.String(required=False)
        deposit_method = DepositMethodEnum(required=True)

    deposit = graphene.Field(DepositNode)

    @gql_login_required()
    def mutate(self, info, amount, deposit_method, description, *args, **kwargs):
        # Deposits are only allowed before 20:00 localtime
        local_time = timezone.localtime(
            timezone.now(), pytz.timezone(settings.TIME_ZONE)
        )

        time_restrictions = check_feature_flag(
            settings.DEPOSIT_TIME_RESTRICTIONS_FEATURE_FLAG, fail_silently=True
        )
        if time_restrictions:
            if not (8 <= local_time.hour <= 20) and not info.context.user.is_at_work:
                raise IllegalOperation(
                    "Deposits are only allowed between 08:00 and 20:00"
                )

        if amount < 1:
            raise IllegalOperation("Minimum deposit amount is 1 kr")

        if amount > 30_000:
            raise IllegalOperation("Maximum deposit amount is 30 000 kr")

        deposit = Deposit(
            account=info.context.user.bank_account,
            amount=amount,
            created_at=timezone.now(),
            description=description,
            deposit_method=deposit_method.value,
        )

        if deposit_method == Deposit.DepositMethod.STRIPE:
            from economy.utils import stripe_create_payment_intent

            check_feature_flag(settings.STRIPE_INTEGRATION_FEATURE_FLAG)
            with transaction.atomic():
                intent, amount_with_fee_in_nok = stripe_create_payment_intent(
                    amount, customer=info.context.user
                )
                deposit.stripe_payment_id = intent.id
                deposit.stripe_payment_intent_status = (
                    Deposit.StripePaymentIntentStatusOptions.CREATED
                )
                deposit.amount = amount_with_fee_in_nok
                deposit.resolved_amount = (
                    amount  # historically used for what is deposited into the account
                )

        elif deposit_method == DepositMethodEnum.BANK_TRANSFER:
            check_feature_flag(settings.BANK_TRANSFER_DEPOSIT_FEATURE_FLAG)
            deposit.resolved_amount = amount
        else:
            raise IllegalOperation("Invalid deposit method")

        deposit.save()
        return CreateDepositMutation(deposit=deposit)


class EconomyMutations(graphene.ObjectType):
    create_soci_product = CreateSociProductMutation.Field()
    patch_soci_product = PatchSociProductMutation.Field()
    delete_soci_product = DeleteSociProductMutation.Field()

    place_product_order = PlaceProductOrderMutation.Field()
    undo_product_order = UndoProductOrderMutation.Field()

    create_soci_session = CreateSociSessionMutation.Field()
    patch_soci_session = PatchSociSessionMutation.Field()
    delete_soci_session = DeleteSociSessionMutation.Field()
    close_soci_session = CloseSociSessionMutation.Field()

    patch_soci_bank_account = PatchSociBankAccountMutation.Field()

    create_deposit = CreateDepositMutation.Field()
    delete_deposit = DeleteDepositMutation.Field()
    approve_deposit = ApproveDepositMutation.Field()
    invalidate_deposit = InvalidateDepositMutation.Field()

    create_soci_order_session = CreateSociOrderSessionMutation.Field()
    place_soci_order_session_order = PlaceSociOrderSessionOrderMutation.Field()
    delete_soci_order_session_food_order = (
        DeleteSociOrderSessionFoodOrderMutation.Field()
    )
    soci_order_session_next_status = SociOrderSessionNextStatusMutation.Field()
    invite_users_to_order_session = InviteUsersToSociOrderSessionMutation.Field()
