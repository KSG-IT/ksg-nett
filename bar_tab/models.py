from django.db import models
from django.db.models import Q


class BarTabProduct(models.Model):
    name = models.CharField(max_length=64, null=False, blank=False)
    price = models.IntegerField()

    def __str__(self):
        return self.name


class BarTabInvoice(models.Model):
    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_sent = models.DateTimeField(null=True, blank=True)
    datetime_settled = models.DateTimeField(null=True, blank=True)
    bar_tab = models.ForeignKey(
        "BarTab", on_delete=models.SET_NULL, related_name="invoices", null=True
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="invoices_created",
        null=True,
    )
    customer = models.ForeignKey("BarTabCustomer", on_delete=models.DO_NOTHING)
    we_owe = models.IntegerField()
    they_owe = models.IntegerField()
    amount = models.IntegerField(help_text="Negative values indicate a refund")
    pdf = models.FileField(upload_to="bar_tab/invoices", null=True, blank=True)

    @property
    def get_invoice_orders(self):
        return self.bar_tab.orders.filter(customer=self.customer)

    def __str__(self):
        return f"Invoice number {self.id} for {self.customer} for {self.amount} on {self.datetime_created}"


class BarTab(models.Model):
    class Status(models.TextChoices):
        OPEN = ("OPEN", "Open")
        LOCKED = ("LOCKED", "Locked")
        UNDER_REVIEW = ("UNDER_REVIEW", "Under review")
        REVIEWED = ("REVIEWED", "Reviewed")

    datetime_opened = models.DateTimeField(auto_now_add=True)
    datetime_closed = models.DateTimeField(null=True, blank=True)
    datetime_reviewed = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.OPEN
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="created_bartabs",
        null=True,
        blank=True,
    )
    closed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="closed_bartabs",
        null=True,
        blank=True,
    )
    reviewed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        related_name="reviewed_bartabs",
        null=True,
        blank=True,
    )

    @classmethod
    def get_active_bar_tab(cls):
        return cls.objects.filter(~Q(status=cls.Status.REVIEWED)).first()

    @property
    def split_orders(self):
        away = self.orders.filter(away=True)
        home = self.orders.filter(away=False)
        return away, home

    def __str__(self):
        return f"Bar tab {self.id}"


class BarTabCustomer(models.Model):
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=32)
    email = models.EmailField()

    def __str__(self):
        return f"{self.name}"


class BarTabOrder(models.Model):
    class Type(models.TextChoices):
        BONG = ("BONG", "Bong")
        LIST = ("LIST", "List")

    created_at = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=4, choices=Type.choices)
    name = models.CharField(max_length=100, default="", null=False, blank=True)
    product = models.ForeignKey(
        BarTabProduct, on_delete=models.CASCADE, related_name="orders"
    )
    customer = models.ForeignKey(
        BarTabCustomer, on_delete=models.CASCADE, related_name="orders"
    )
    away = models.BooleanField(
        default=False, help_text="If true this is us at another 'customer'"
    )
    quantity = models.IntegerField()
    cost = models.IntegerField()
    bar_tab = models.ForeignKey(BarTab, on_delete=models.CASCADE, related_name="orders")
    reviewed = models.BooleanField(default=False)

    @property
    def get_name_display(self):
        if self.type == self.Type.BONG:
            return self.get_type_display()
        return self.name

    @property
    def purchased_where(self):
        if self.away:
            return "Borte"

        return "Hjemme"

    def __str__(self):
        return f"{self.get_name_display} {self.purchased_where}for {self.customer} at {self.bar_tab}"
