import os
import datetime
from typing import Union, Dict, List, Optional
from django.core.validators import MinValueValidator
from django.conf import settings
from django.db import models
from django.db.models import QuerySet
from django.utils import timezone
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel, TimeFramedModel
import common.models as common_models

from api.exceptions import NoSociSessionError
from users.models import User


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

    objects = models.Manager()
    soci_master_account = QueryManager(card_uuid=settings.SOCI_MASTER_ACCOUNT_CARD_ID)

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
        return self.user.username in settings.SOCI_GOLD

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


class SociProduct(TimeFramedModel):
    """
    A product for sale at Soci.
    Each product must have a unique SKU (stock keeping unit) identifier that enables us
    to differentiate between different products in the Soci stock keeping system.
    """

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

    class Type(models.TextChoices):
        SOCIETETEN = ("SOCIETETEN", "Societeten")
        STILLETIME = ("STILLETIME", "Stilletime")
        KRYSELLISTE = ("KRYSSELISTE", "Krysseliste")

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


class Transfer(TimeStampedModel):
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

    def __str__(self):
        return f"Transfer from {self.source.user} to {self.destination.user} of {self.amount} kr"

    def __repr__(self):
        return f"Transfer(from={self.source.user},to={self.destination.user},amount={self.amount})"


class Deposit(common_models.TimestampedModel):
    """
    A deposit of money into a Soci bank account.
    Deposits need a valid receipt in order to be approved.
    """

    def _receipt_upload_location(self, filename):
        return os.path.join("receipts", filename)

    account = models.ForeignKey(
        "SociBankAccount",
        related_name="deposits",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    description = models.TextField(default="", blank=True)
    amount = models.IntegerField(blank=False, null=False)
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


class DepositComment(TimeStampedModel):
    """
    A comment made by some user on a deposit.
    This is useful in cases where a deposit is incomplete by missing a receipt or similar.
    """

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

    def __str__(self):
        # Add ellipses for comments longer than 20 characters
        shortened_comment = self.comment[0:20] + (self.comment[20:] and "..")
        return (
            f'Comment "{shortened_comment}" by {self.user.get_full_name()} '
            f"on deposit by {self.deposit.account.user.get_full_name()}"
        )

    def __repr__(self):
        return f"DepositComment(id={self.id},deposit={self.deposit.id},user={self.user.id},comment={self.comment})"

    class Meta:
        pass
