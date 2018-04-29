import os
from typing import Union, Optional

from django.conf import settings
from django.db import models
from django.db.models import QuerySet, Q

from users.models import User


class Transaction(models.Model):
    source = models.ForeignKey('economy.SociBankAccount', related_name='source_transactions', blank=True, null=True,
                               on_delete=models.SET_NULL)
    destination = models.ForeignKey('economy.SociBankAccount', related_name='destination_transactions', blank=True,
                                    null=True, on_delete=models.SET_NULL)

    amount = models.IntegerField(blank=False, null=False)
    product = models.ForeignKey('economy.SociProduct', blank=True, null=True, on_delete=models.SET_NULL)

    signed_off_by = models.ForeignKey(User, null=True, related_name='verified_transactions')
    signed_off_time = models.DateTimeField(auto_now_add=True)

    @property
    def is_valid(self):
        return self.signed_off_by is not None

    def __str__(self):
        return f"Transaction from {self.source.user} to {self.destination.user} of {self.amount} kr"

    def __repr__(self):
        return f"Transaction(from={self.source.user}, to={self.destination.user}, amount={self.amount})"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.source:
            self.source.remove_funds(amount=self.amount)
        if self.destination:
            self.destination.add_funds(amount=self.amount)
        super().save(force_insert, force_update, using, update_fields)


class Deposit(models.Model):
    def _receipt_upload_location(self, filename):
        return os.path.join('receipts', str(self.id), filename)

    account = models.ForeignKey('economy.SociBankAccount', related_name='deposits', blank=True, null=True,
                                on_delete=models.SET_NULL)
    amount = models.IntegerField(blank=False, null=False)
    receipt = models.ImageField(upload_to=_receipt_upload_location, blank=True, null=True, default=None)
    signed_off_by = models.ForeignKey(User, null=True, blank=True, related_name='verified_deposits')
    signed_off_time = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    @property
    def is_valid(self):
        return self.signed_off_by is not None

    def __str__(self):
        return f"Deposit for {self.account.user} of {self.amount} kr"

    def __repr__(self):
        return f"Deposit(person={self.account.user},amount={self.amount})"


class SociBankAccount(models.Model):
    """
    A bank account account in Societeten, used for storing available
    balance and tracking transactions for a KSG user.
    """
    user = models.OneToOneField(User, related_name='bank_account', blank=False, null=False, on_delete=models.CASCADE)
    balance = models.IntegerField(default=0)
    card_uuid = models.BigIntegerField(blank=True, null=True, default=None, unique=True)
    display_balance_at_soci = models.BooleanField(default=False)

    @property
    def has_sufficient_funds(self) -> bool:
        return self.balance > settings.MINIMUM_SOCI_AMOUNT

    @property
    def transaction_history(self) -> Union[QuerySet, 'Transaction']:
        return Transaction.objects.filter(Q(source=self) | Q(destination=self))

    @property
    def public_balance(self) -> Optional[int]:
        return self.balance if self.display_balance_at_soci else None

    def __str__(self):
        return f"Soci Bank Account for {self.user} containing {self.balance} kr"

    def __repr__(self):
        return f"BankAccount(person={self.user},balance={self.balance})"

    def add_funds(self, amount: int):
        self.balance += amount
        self.save()

    def remove_funds(self, amount: int):
        self.balance -= amount
        self.save()


class SociProduct(models.Model):
    """
    A product for sale at Soci
    """
    sku_number = models.CharField(primary_key=True, unique=True, max_length=50, verbose_name='Product SKU number')
    name = models.CharField(max_length=50)
    price = models.IntegerField()
    description = models.TextField(blank=True, null=True, default=None, max_length=200)
    icon = models.CharField(max_length=100)

    def __str__(self):
        return f"SociProduct {self.name} costing {self.price} kr"

    def __repr__(self):
        return f"SociProduct(name={self.name},price={self.price})"
