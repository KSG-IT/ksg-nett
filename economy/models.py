from django.db import models

from users.models import User

import os


def get_image_path(instance, filename):
    return os.path.join('photos', str(instance.id), filename)


class Transaction(models.Model):
    sender = models.ForeignKey(User, blank=False, null=False, related_name='sent_transactions')
    recipient = models.ForeignKey(User, blank=False, null=False, related_name='received_transactions')
    amount = models.IntegerField(blank=False, null=False)

    signed_off_by = models.ForeignKey(User, null=True, related_name='verified_transactions')
    signed_off_time = models.DateTimeField(null=True, blank=True)

    @property
    def valid(self):
        return self.signed_off_by is not None

    @property
    def invalid(self):
        return not self.valid

    def __str__(self):
        return "Transaction from %s to %s of %d NOK" % (self.sender.username, self.recipient.username, self.amount)

    def __repr__(self):
        return "Transaction(from=%s, to=%s, amount=%d)" % (self.sender.username, self.recipient.username, self.amount)


class Deposit(models.Model):
    person = models.ForeignKey(User, blank=False, null=False)
    amount = models.IntegerField(blank=False, null=False)
    receipt = models.ImageField(upload_to=get_image_path, blank=True, null=True)
    signed_off_by = models.ForeignKey(User, null=True, blank=True, related_name='verified_deposits')
    signed_off_time = models.DateTimeField(null=True, blank=True)

    @property
    def valid(self):
        return self.signed_off_by is not None

    @property
    def invalid(self):
        return not self.valid

    def __str__(self):
        return "Deposit by %s of %d NOK" % (self.person.username, self.amount)

    def __repr__(self):
        return "Group(person=%s,amount=%d)" % (self.person.username, self.amount)


class Product(models.Model):
    product_name = models.CharField(primary_key=True, max_length=50, blank=False, null=False, unique=True)
    price = models.IntegerField(blank=False, null=False)

    def __str__(self):
        return "A product with name %s with the price of %d NOK" % (self.product_name, self.price)

    def __repr__(self):
        return "Product(product_name=%s, price=%d)" % (self.product_name, self.price)


class PurchaseList(models.Model):
    date_registered = models.DateField(auto_now_add=True, blank=False, null=False)
    date_purchased = models.DateField(auto_now_add=True, blank=False, null=False)
    signed_off_by = models.ForeignKey(User, blank=False, null=False)
    comment = models.CharField(max_length=100, blank=False, null=False)

    def __str__(self):
        return "A list of items purchased at date %s, registered at date %s by person %s" % \
               (self.date_purchased, self.date_registered, self.signed_off_by.username)

    def __repr__(self):
        return "PurchaseList(date_crossed=%s, date_registered=%s, signed_off_by=%s, comment=%s)" % \
               (self.date_purchased, self.date_registered, self.signed_off_by.username, self.comment)


class Purchase(models.Model):
    person = models.ForeignKey(User, blank=True, null=True)
    product = models.ForeignKey(Product, blank=False, null=False)
    amount = models.IntegerField(blank=False, null=False)
    purchase_list = models.ForeignKey(PurchaseList, on_delete=models.CASCADE)

    def __str__(self):
        return "A purchase by person %s of %d number of product %s" % (self.person.username,
                                                                       self.amount,
                                                                       self.product.product_name)

    def __repr__(self):
        return "Purchase(person=%s, product=%s, amount=%d, purchase_list=%d)" % (self.person.username,
                                                                                 self.product.product_name,
                                                                                 self.amount,
                                                                                 self.purchase_list.id)


