from django.contrib import admin

from economy.models import Deposit, SociBankAccount, SociProduct, SociSession, ProductOrder


@admin.register(SociBankAccount)
class SociBankAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'card_uuid', 'balance']
    readonly_fields = ['balance']


@admin.register(SociProduct)
class SociProductAdmin(admin.ModelAdmin):
    list_display = ['sku_number', 'icon', 'name', 'price', 'description', 'start']


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

@admin.register(ProductOrder)
class ProductOrderAdmin(admin.ModelAdmin):
    pass
