from django.db import models

from users.models import User


class Transaction(models.Model):
    sender = models.ForeignKey(User, blank=False, null=False, related_name='sent_transactions')
    recipient = models.ForeignKey(User, blank=False, null=False, related_name='received_transactions')
    amount = models.IntegerField(blank=False, null=False)

    signed_off_by = models.ForeignKey(User, null=True, related_name='verified_transactions')
    signed_off_time = models.DateTimeField(auto_now_add=True)

    @property
    def valid(self):
        return self.signed_off_by is not None

    @property
    def invalid(self):
        return not self.valid

    def __str__(self):
        return "Transaction from %s to %s of %d NOK" % (self.sender.name, self.recipient.name, self.amount)

    def __repr__(self):
        return "Transaction(from=%s, to=%s, amount=%d)" % (self.sender.name, self.recipient.name, self.amount)


class Deposit(models.Model):
    person = models.ForeignKey(User, blank=False, null=False)
    amount = models.IntegerField(blank=False, null=False)

    signed_off_by = models.ForeignKey(User, null=True, blank=True, related_name='verified_deposits')
    signed_off_time = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    @property
    def valid(self):
        return self.signed_off_by is not None

    @property
    def invalid(self):
        return not self.valid

    def __str__(self):
        return "Deposit for %s of %d NOK" % (self.person.name, self.amount)

    def __repr__(self):
        return "Group(person=%s,amount=%d)" % (self.person.name, self.amount)
