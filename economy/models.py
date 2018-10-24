import os
from typing import Union, Optional, Dict, List

from django.conf import settings
from django.db import models
from django.db.models import QuerySet

from economy.managers import SociBankAccountManager
from users.models import User


class SociBankAccount(models.Model):
    """
    A bank account account in Societeten, used for storing available
    balance and tracking transactions for a KSG user.
    """
    user = models.OneToOneField(
        User,
        related_name='bank_account',
        blank=False,
        null=False,
        on_delete=models.CASCADE
    )

    balance = models.IntegerField(default=0)
    card_uuid = models.BigIntegerField(blank=True, null=True, default=None, unique=True)
    display_balance_at_soci = models.BooleanField(default=False)

    objects = SociBankAccountManager()

    @property
    def has_sufficient_funds(self) -> bool:
        return self.balance > settings.MINIMUM_SOCI_AMOUNT

    @property
    def transaction_history(self) -> Dict[str, Union[QuerySet, 'Purchase', 'Transfer', 'Deposit']]:
        return {
            'purchases': self.purchases.all(),
            'transfers': self.source_transfers.all() | self.destination_transfers.all(),
            'deposits': self.deposits.all()
        }

    @property
    def public_balance(self) -> Optional[int]:
        return self.balance if self.display_balance_at_soci else None

    @property
    def chargeable_balance(self) -> int:
        return max(self.balance - settings.MINIMUM_SOCI_AMOUNT, settings.MINIMUM_SOCI_AMOUNT)

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


class SociProduct(models.Model):
    """
    A product for sale at Soci.
    Each product must have a unique SKU (stock keeping unit) identifier that enables us
    to differentiate between different products in the Soci stock keeping system.
    """
    sku_number = models.CharField(unique=True, max_length=50, verbose_name='Product SKU number')
    name = models.CharField(max_length=50)
    price = models.IntegerField()
    description = models.TextField(blank=True, null=True, default=None, max_length=200)
    icon = models.CharField(max_length=100, blank=True, null=True)
    expiry_date = models.DateTimeField(blank=True, null=True, default=None)

    def __str__(self):
        return f"SociProduct {self.name} costing {self.price} kr"

    def __repr__(self):
        return f"SociProduct(name={self.name},price={self.price})"


class ProductOrder(models.Model):
    """
    An order for a specific Soci product, and the order size.
    If the product is direct charge, direct_charge_amount is used to specify the amount.
    """
    product = models.ForeignKey(
        'SociProduct',
        on_delete=models.CASCADE
    )

    order_size = models.IntegerField(default=1)
    amount = models.IntegerField()

    purchase = models.ForeignKey(
        'Purchase',
        related_name='product_orders',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f"Order of {self.order_size} {self.product.name}(s)"

    def __repr__(self):
        return f"Order(product={self.product}, order_size={self.order_size})"


class Purchase(models.Model):
    """
    A transfer from a personal Soci bank account to the Soci master account.
    Each purchase object can contain multiple ProductOrders.
    """
    source = models.ForeignKey(
        'SociBankAccount',
        related_name='purchases',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )

    signed_off_by = models.ForeignKey(
        User,
        null=True,
        related_name='verified_purchases',
        on_delete=models.DO_NOTHING
    )
    signed_off_time = models.DateTimeField(auto_now_add=True)

    collection = models.ForeignKey(
        'PurchaseCollection',
        related_name='purchases',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )

    @property
    def is_valid(self) -> bool:
        return self.signed_off_by is not None

    @property
    def total_amount(self) -> int:
        total_amount = 0
        for order in self.product_orders.all():
            total_amount += order.order_size * order.amount

        return total_amount

    @property
    def products_purchased(self) -> List[str]:
        return [order.product.name for order in self.product_orders.all()]

    def __str__(self):
        return f"Purchase by {self.source.user} of {self.total_amount} kr"

    def __repr__(self):
        return f"Purchase(user={self.source.user},amount={self.total_amount})"


class PurchaseCollection(models.Model):
    """
    A collection of Purchases made within a specified time period.
    """
    name = models.CharField(max_length=50, blank=True, null=True)

    start_period = models.DateTimeField(auto_now_add=True)
    end_period = models.DateTimeField(blank=True, null=True, default=None)

    @property
    def total_purchases(self) -> int:
        return self.purchases.count()

    @property
    def total_amount(self) -> int:
        total_amount = 0
        for purchase in self.purchases.all():
            total_amount += purchase.total_amount

        return total_amount

    def __str__(self):
        return f"PurchaseCollection {self.name} containing {self.purchases.count()} purchases " \
               f"between {self.start_period} and {self.end_period}"

    def __repr__(self):
        return f"PurchaseCollection(name={self.name},start={self.start_period},end={self.end_period})"


class Transfer(models.Model):
    """
    A transfer between two personal Soci bank accounts.
    """
    source = models.ForeignKey(
        'SociBankAccount',
        related_name='source_transfers',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )

    destination = models.ForeignKey(
        'SociBankAccount',
        related_name='destination_transfers',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )

    amount = models.IntegerField(blank=False, null=False)

    def __str__(self):
        return f"Transfer from {self.source.user} to {self.destination.user} of {self.amount} kr"

    def __repr__(self):
        return f"Transfer(from={self.source.user},to={self.destination.user},amount={self.amount})"


class Deposit(models.Model):
    """
    A deposit of money into a Soci bank account.
    Deposits need a valid receipt in order to be approved.
    """

    def _receipt_upload_location(self, filename):
        return os.path.join('receipts', str(self.id), filename)

    account = models.ForeignKey(
        'SociBankAccount',
        related_name='deposits',
        blank=True,
        null=True,
        on_delete=models.SET_NULL
    )

    amount = models.IntegerField(blank=False, null=False)
    receipt = models.ImageField(upload_to=_receipt_upload_location, blank=True, null=True, default=None)

    signed_off_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name='verified_deposits',
        on_delete=models.DO_NOTHING
    )
    signed_off_time = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    @property
    def is_valid(self):
        return self.signed_off_by is not None

    def __str__(self):
        return f"Deposit for {self.account.user} of {self.amount} kr"

    def __repr__(self):
        return f"Deposit(person={self.account.user},amount={self.amount})"