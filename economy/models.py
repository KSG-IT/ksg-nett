import os
from typing import Union, Dict, Optional
from django.core.validators import MinValueValidator
from django.conf import settings
from django.db import models
from django.db.models import QuerySet
from django.utils import timezone
import common.models as common_models
from django.utils.translation import gettext_lazy as _

from bar_tab.models import BarTabCustomer
from users.models import User
from secrets import token_urlsafe
import qrcode


class SociBankAccount(models.Model):
    """
    A bank account account in Societeten, used for storing available
    balance and tracking transactions for a KSG user.
    """

    user = models.OneToOneField(
        User,
        related_name="bank_account",
        blank=False,
        null=False,
        on_delete=models.CASCADE,
    )

    balance = models.IntegerField(default=0, editable=False)
    card_uuid = models.CharField(max_length=50, blank=True, null=True, unique=True)
    external_charge_secret = models.CharField(max_length=64, null=True, blank=True)

    objects = models.Manager()

    @property
    def soci_master_account(self):
        return self.objects.get(card__uuid=settings.SOCI_MASTER_ACCOUNT_CARD_ID)

    @property
    def transaction_history(
        self,
    ) -> Dict[str, Union[QuerySet, "ProductOrder", "Transfer", "Deposit"]]:
        return {
            "product_orders": self.product_orders.all(),  # .prefetch_related("product"),
            "transfers": self.source_transfers.all() | self.destination_transfers.all(),
            "deposits": self.deposits.all(),
        }

    @classmethod
    def get_wanted_list(cls):
        return (
            User.objects.filter(
                bank_account__balance__lte=settings.WANTED_LIST_THRESHOLD
            )
            .exclude(is_active=False)
            .exclude(username__in=settings.SOCI_GOLD)
            .order_by("bank_account__balance")
        )

    @property
    def is_gold(self):
        if self.user.is_superuser:
            return True

        return (
            self.user.username in settings.SOCI_GOLD
            or self.user.email in settings.SOCI_GOLD
        )

    def __str__(self):
        return f"Soci Bank Account for {self.user} containing {self.balance} kr"

    def __repr__(self):
        return f"BankAccount(person={self.user},balance={self.balance})"

    def add_funds(self, amount: int):
        self.balance += amount
        self.save()

    # This intentionally allows setting a negative balance
    def remove_funds(self, amount: int):
        self.balance -= amount
        self.save()

    @property
    def money_spent(self) -> int:
        purchases = self.product_orders.all().aggregate(models.Sum("cost"))
        return purchases["cost__sum"] or 0

    def regenerate_external_charge_secret(self):
        self.external_charge_secret = token_urlsafe(32)
        self.save()
        return self.external_charge_secret


class SociProduct(models.Model):
    """
    A product for sale at Soci.
    Each product must have a unique SKU (stock keeping unit) identifier that enables us
    to differentiate between different products in the Soci stock keeping system.
    """

    class Type(models.TextChoices):
        FOOD = "FOOD", "Food"
        DRINK = "DRINK", "Drink"

    type = models.CharField(
        max_length=10,
        choices=Type.choices,
        null=True,
    )
    sku_number = models.CharField(
        unique=True, max_length=50, verbose_name="Product SKU number"
    )
    name = models.CharField(max_length=50)
    price = models.IntegerField()
    description = models.TextField(blank=True, null=True, default=None, max_length=200)
    icon = models.CharField(max_length=2, blank=True, null=True)
    default_stilletime_product = models.BooleanField(default=False)
    hide_from_api = models.BooleanField(default=False)
    sg_id = models.IntegerField(blank=True, null=True, default=None, unique=True)
    start = models.DateTimeField(_("start"), null=True, blank=True)
    end = models.DateTimeField(_("end"), null=True, blank=True)

    def __str__(self):
        return f"SociProduct {self.name} costing {self.price} kr"

    def __repr__(self):
        return f"SociProduct(name={self.name},price={self.price})"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if self._state.adding:
            self.start = self.start or timezone.now()
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )


class SociSession(models.Model):
    """
    A collection of Purchases made within a specified time period.
    Every session has a user that signed off, i.e. who authenticated the session.
    """

    class Meta:
        permissions = [
            ("can_overcharge", "Can overcharge"),
        ]

    class Type(models.TextChoices):
        SOCIETETEN = ("SOCIETETEN", "Societeten")
        STILLETIME = ("STILLETIME", "Stilletime")
        KRYSELLISTE = ("KRYSSELISTE", "Krysseliste")
        BURGERLISTE = ("BURGERLISTE", "Burgerliste")

    name = models.CharField(max_length=50, blank=True, null=True)
    created_by = models.ForeignKey(
        to="users.User", null=True, on_delete=models.SET_NULL
    )
    type = models.CharField(
        choices=Type.choices,
        default=Type.SOCIETETEN,
        max_length=20,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Manual lists have sense of timestamps and can be registered at later dates
    creation_date = models.DateField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(blank=True, null=True)

    @property
    def closed(self):
        return self.closed_at is not None

    @classmethod
    def get_active_session(cls) -> Optional["SociSession"]:
        """
        Get the active session that should be used for all purchases, or None if no such session exists.
        """
        return (
            cls.objects.filter(closed_at__isnull=True, type=cls.Type.SOCIETETEN)
            .order_by("-created_at")
            .last()
        )

    @classmethod
    def terminate_active_session(cls):
        """
        Set an end date for the currently active session, thus terminating it.
        """
        active_session = cls.get_active_session()
        if active_session:
            if active_session.product_orders.all().exists():
                active_session.closed_at = timezone.now()
                active_session.save()
            else:
                # Nothing sold in session, we delete it
                active_session.delete()

    @property
    def total_product_orders(self) -> int:
        return self.product_orders.count()

    @property
    def total_revenue(self) -> int:

        purchase_sums = [order.cost for order in self.product_orders.all()]
        return sum(purchase_sums)

    def __str__(self):
        return (
            f"SociSession {self.name} containing {self.product_orders.count()} product_orders "
            f"between {self.created_at} and {self.closed_at}"
        )

    def __repr__(self):
        return f"SociSession(name={self.name},start={self.created_at},end={self.closed_at})"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if self._state.adding:
            self.created_at = timezone.now()
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )


class ProductOrder(models.Model):
    """
    An order for a specific Soci product, and the order size.
    """

    class Meta:
        verbose_name = "Product order"
        verbose_name_plural = "Product orders"
        indexes = (models.Index(fields=["session", "source"]),)

    product = models.ForeignKey("SociProduct", on_delete=models.CASCADE)

    order_size = models.IntegerField(
        default=1, validators=[MinValueValidator(limit_value=1)]
    )
    source = models.ForeignKey(
        "SociBankAccount",
        related_name="product_orders",
        blank=False,
        null=False,
        on_delete=models.CASCADE,
    )

    session = models.ForeignKey(
        "SociSession",
        related_name="product_orders",
        on_delete=models.DO_NOTHING,
        default=SociSession.get_active_session,
    )

    purchased_at = models.DateTimeField(auto_now_add=True)
    cost = models.IntegerField(validators=[MinValueValidator(limit_value=1)])

    def __str__(self):
        return f"Order of {self.order_size} {self.product.name}(s)"

    def __repr__(self):
        return f"Order(product={self.product}, order_size={self.order_size})"


class Transfer(models.Model):
    """
    A transfer between two personal Soci bank accounts.
    """

    source = models.ForeignKey(
        "SociBankAccount",
        related_name="source_transfers",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    destination = models.ForeignKey(
        "SociBankAccount",
        related_name="destination_transfers",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    amount = models.IntegerField(blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transfer from {self.source.user} to {self.destination.user} of {self.amount} kr"

    def __repr__(self):
        return f"Transfer(from={self.source.user},to={self.destination.user},amount={self.amount})"


class Deposit(common_models.TimestampedModel):
    """
    A deposit of money into a Soci bank account.
    Deposits need a valid receipt in order to be approved.
    """

    class Meta:
        permissions = (
            ("approve_deposit", "Can approve deposits"),
            ("invalidate_deposit", "Can invalidate deposits"),
        )

    def _receipt_upload_location(self, filename):
        return os.path.join("receipts", filename)

    class StripePaymentIntentStatusOptions(models.TextChoices):
        CREATED = "CREATED"
        SUCCESS = "SUCCESS"

    class DepositMethod(models.TextChoices):
        VIPPS = "VIPPS"
        BANK_TRANSFER = "BANK_TRANSFER"
        STRIPE = "STRIPE"

    stripe_payment_intent_status = models.CharField(
        choices=StripePaymentIntentStatusOptions.choices,
        default=StripePaymentIntentStatusOptions.CREATED,
        max_length=32,
        null=True,
        blank=True,
    )
    stripe_payment_id = models.CharField(max_length=64, null=True, blank=True)

    account = models.ForeignKey(
        "SociBankAccount",
        related_name="deposits",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    deposit_method = models.CharField(
        choices=DepositMethod.choices, max_length=32, null=True, blank=True
    )
    description = models.TextField(default="", blank=True)
    amount = models.IntegerField(
        blank=False, null=False, help_text="Amount paid by customer"
    )
    resolved_amount = models.IntegerField(
        blank=True,
        null=True,
        help_text="Amount after deducting stripe fee's and flooring to a whole number, if applicable.",
    )
    receipt = models.ImageField(
        upload_to=_receipt_upload_location, blank=True, null=True, default=None
    )

    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name="verified_deposits",
        on_delete=models.DO_NOTHING,
    )
    approved_at = models.DateTimeField(default=None, null=True, blank=True)

    @classmethod
    def get_pending_deposits(cls):
        return cls.objects.filter(approved=False)

    def __str__(self):
        return f"Deposit for {self.account.user} of {self.amount} kr"

    def __repr__(self):
        return f"Deposit(person={self.account.user},amount={self.amount})"


class DepositComment(models.Model):
    """
    A comment made by some user on a deposit.
    This is useful in cases where a deposit is incomplete by missing a receipt or similar.
    """

    class Meta:
        pass

    deposit = models.ForeignKey(
        Deposit,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        User,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="all_deposit_comments",
    )
    comment = models.TextField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Add ellipses for comments longer than 20 characters
        shortened_comment = self.comment[0:20] + (self.comment[20:] and "..")
        return (
            f'Comment "{shortened_comment}" by {self.user.get_full_name()} '
            f"on deposit by {self.deposit.account.user.get_full_name()}"
        )

    def __repr__(self):
        return f"DepositComment(id={self.id},deposit={self.deposit.id},user={self.user.id},comment={self.comment})"


class SociOrderSession(models.Model):
    class Meta:
        verbose_name = "Soci Order Session"
        verbose_name_plural = "Soci Order Sessions"

    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        FOOD_ORDERING = "FOOD_ORDERING", "Food Ordering"
        DRINK_ORDERING = "DRINK_ORDERING", "Drink Ordering"
        CLOSED = "CLOSED", "Closed"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="soci_order_sessions_created",
    )
    closed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="soci_order_sessions_closed",
    )
    invited_users = models.ManyToManyField(
        User,
        related_name="soci_order_sessions_invited_to",
        blank=True,
    )
    order_pdf = models.FileField(
        upload_to="soci_order_sessions",
        null=True,
        blank=True,
    )

    @classmethod
    def get_active_session(cls):
        # Get any session that is not closed
        return cls.objects.filter(
            status__in=[
                cls.Status.CREATED,
                cls.Status.FOOD_ORDERING,
                cls.Status.DRINK_ORDERING,
            ]
        ).first()


class SociOrderSessionOrder(models.Model):
    class Meta:
        verbose_name = "Soci Order Session Order"
        verbose_name_plural = "Soci Order Session Orders"

    session = models.ForeignKey(
        SociOrderSession,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    user = models.ForeignKey(
        User,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="soci_order_session_orders",
    )
    product = models.ForeignKey(
        SociProduct,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="user_session_orders",
    )
    amount = models.IntegerField(null=False, blank=False)
    ordered_at = models.DateTimeField(auto_now_add=True)


class ExternalCharge(models.Model):
    class Meta:
        verbose_name = "External Charge"
        verbose_name_plural = "External Charges"

    bar_tab_customer = models.ForeignKey(
        BarTabCustomer,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="external_charges",
    )
    amount = models.IntegerField(null=False, blank=False)
    reference = models.CharField(default="", max_length=255, blank=True)
    bank_account = models.ForeignKey(
        SociBankAccount,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="external_charges",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    webhook_attempts = models.IntegerField(default=0)
    webhook_success = models.BooleanField(default=False)
