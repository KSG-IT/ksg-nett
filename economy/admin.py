from django.contrib import admin

from economy.models import Deposit, SociBankAccount, SociProduct, Purchase, SociSession


@admin.register(SociBankAccount)
class SociBankAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'card_uuid', 'balance']
    readonly_fields = ['balance']


@admin.register(SociProduct)
class SociProductAdmin(admin.ModelAdmin):
    list_display = ['sku_number', 'icon', 'name', 'price', 'description', 'start']


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['user', 'sum', 'session']
    readonly_fields = ['sum', 'orders']
    raw_id_fields = ['source', 'session']

    @staticmethod
    def user(purchase):
        return purchase.source.user

    @staticmethod
    def sum(purchase):
        return purchase.total_amount

    @staticmethod
    def orders(purchase: Purchase):
        product_orders = purchase.product_orders.values_list('product__name', 'order_size')
        return "\n".join(f"{product}: {amount}" for product, amount in product_orders)


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'amount', 'has_receipt', 'is_valid']

    @staticmethod
    def user(deposit: Deposit):
        return deposit.account.user

    def has_receipt(self, deposit):
        return bool(deposit.receipt)

    has_receipt.boolean = True

    def is_valid(self, deposit):
        return deposit.is_valid

    is_valid.boolean = True


@admin.register(SociSession)
class SociSessionAdmin(admin.ModelAdmin):
    pass
