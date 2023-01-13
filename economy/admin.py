from django.contrib import admin

from economy.models import (
    Deposit,
    SociBankAccount,
    SociProduct,
    SociSession,
    ProductOrder,
    Transfer,
    SociOrderSession,
    SociOrderSessionOrder,
)


@admin.register(SociBankAccount)
class SociBankAccountAdmin(admin.ModelAdmin):
    list_display = ["user", "card_uuid", "balance"]
    readonly_fields = ["balance"]


@admin.register(SociProduct)
class SociProductAdmin(admin.ModelAdmin):
    list_display = ["sku_number", "icon", "name", "price", "description", "start"]


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ["source", "destination", "amount", "created_at"]


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "amount", "has_receipt", "approved"]

    @staticmethod
    def user(deposit: Deposit):
        return deposit.account.user

    def has_receipt(self, deposit):
        return bool(deposit.receipt)

    has_receipt.boolean = True

    def approved(self, deposit):
        return deposit.approved

    approved.boolean = True


@admin.register(SociSession)
class SociSessionAdmin(admin.ModelAdmin):
    pass


@admin.register(ProductOrder)
class ProductOrderAdmin(admin.ModelAdmin):
    list_display = ["id", "product", "order_size", "source", "cost"]
    search_fields = [
        "source__user__username",
        "source__user__first_name",
        "source__user__last_name",
    ]

    @staticmethod
    def cost(product_order: ProductOrder):
        return product_order.cost


@admin.register(SociOrderSession)
class SociOrderSessionAdmin(admin.ModelAdmin):
    pass


@admin.register(SociOrderSessionOrder)
class UserSociOrderSessionCollectionAdmin(admin.ModelAdmin):
    pass
