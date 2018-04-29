from django.contrib import admin

from economy.models import Transaction, Deposit, SociBankAccount, SociProduct

admin.site.register(Transaction)
admin.site.register(Deposit)


class SociBankAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'card_uuid', 'format_balance', 'sufficient_funds']

    def format_balance(self, obj):
        return obj.formatted_balance

    def sufficient_funds(self, obj):
        return obj.has_sufficient_funds

    format_balance.short_description = 'Balance'
    sufficient_funds.boolean = True


class SociProductAdmin(admin.ModelAdmin):
    list_display = ['sku_number', 'name', 'format_price', 'description']

    def format_price(self, obj):
        return obj.formatted_price

    format_price.short_description = 'Price'


admin.site.register(SociBankAccount, SociBankAccountAdmin)
admin.site.register(SociProduct, SociProductAdmin)
