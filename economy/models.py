import os
from typing import Union, Dict, List, Optional

from django.conf import settings
from django.db import models
from django.db.models import QuerySet
from django.utils import timezone
from model_utils.fields import MonitorField
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel, TimeFramedModel

from api.exceptions import NoSociSessionError
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

    balance = models.IntegerField(default=0, editable=False)
    card_uuid = models.CharField(max_length=50, blank=True, null=True, default=None, unique=True)

    objects = models.Manager()
    soci_master_account = QueryManager(card_uuid=settings.SOCI_MASTER_ACCOUNT_CARD_ID)

    @property
    def transaction_history(self) -> Dict[str, Union[QuerySet, 'Purchase', 'Transfer', 'Deposit']]:
        return {
            'purchases': self.purchases.all(),
            'transfers': self.source_transfers.all() | self.destination_transfers.all(),
            'deposits': self.deposits.all()
        }

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


class SociProduct(TimeFramedModel):
    """
    A product for sale at Soci.
    Each product must have a unique SKU (stock keeping unit) identifier that enables us
    to differentiate between different products in the Soci stock keeping system.
    """
    sku_number = models.CharField(unique=True, max_length=50, verbose_name='Product SKU number')
    name = models.CharField(max_length=50)
    price = models.IntegerField()
    description = models.TextField(blank=True, null=True, default=None, max_length=200)
    icon = models.CharField(max_length=1, blank=True, null=True)

    def __str__(self):
        return f"SociProduct {self.name} costing {self.price} kr"

    def __repr__(self):
        return f"SociProduct(name={self.name},price={self.price})"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self._state.adding:
            self.start = self.start or timezone.now()
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


class SociSession(TimeFramedModel):
    """
    A collection of Purchases made within a specified time period.
    Every session has a user that signed off, i.e. who authenticated the session.
    """
    name = models.CharField(max_length=50, blank=True, null=True)
    signed_off_by = models.ForeignKey(to='users.User', null=True, on_delete=models.DO_NOTHING)

    @classmethod
    def get_active_session(cls) -> Optional['SociSession']:
        """
        Get the active session that should be used for all purchases, or None if no such session exists.
        """
        return cls.objects.filter(end__isnull=True).order_by('-start').last()

    @classmethod
    def terminate_active_session(cls):
        """
        Set an end date for the currently active session, thus terminating it.
        """
        active_session = cls.get_active_session()
        if active_session:
            active_session.end = timezone.now()
            active_session.save()

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
        return f"SociSession {self.name} containing {self.purchases.count()} purchases " \
            f"between {self.start} and {self.end}"

    def __repr__(self):
        return f"SociSession(name={self.name},start={self.start},end={self.end})"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self._state.adding:
            self.start = timezone.now()
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


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

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self._state.adding:
            order_amount = self.amount * self.order_size
            self.purchase.source.remove_funds(amount=order_amount)
            SociBankAccount.soci_master_account.get().add_funds(amount=order_amount)

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


class Purchase(TimeStampedModel):
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

    session = models.ForeignKey(
        'SociSession',
        related_name='purchases',
        on_delete=models.DO_NOTHING,
        default=SociSession.get_active_session
    )

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

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self._state.adding and self.session is None:
            raise NoSociSessionError()

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


class Transfer(TimeStampedModel):
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


class Deposit(TimeStampedModel):
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
    description = models.TextField(blank=True)
    amount = models.IntegerField(blank=False, null=False)
    receipt = models.ImageField(upload_to=_receipt_upload_location, blank=True, null=True, default=None)

    signed_off_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name='verified_deposits',
        on_delete=models.DO_NOTHING
    )
    signed_off_time = MonitorField(monitor='signed_off_by', null=True, default=None)

    @property
    def is_valid(self):
        return self.signed_off_by is not None

    def __str__(self):
        return f"Deposit for {self.account.user} of {self.amount} kr"

    def __repr__(self):
        return f"Deposit(person={self.account.user},amount={self.amount})"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.is_valid and not self.signed_off_time:
            self.account.add_funds(self.amount)

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)




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
        return f'Comment "{shortened_comment}" by {self.user.get_full_name()} ' \
            f'on deposit by {self.deposit.account.user.get_full_name()}'

    def __repr__(self):
        return f"DepositComment(id={self.id},deposit={self.deposit.id},user={self.user.id},comment={self.comment})"

    class Meta:
        pass
