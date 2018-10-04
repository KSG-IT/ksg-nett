from django.contrib import admin

from economy.models import Transfer, Deposit, SociBankAccount, SociProduct

admin.site.register(Transfer)
admin.site.register(Deposit)


class SociBankAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'card_uuid', 'balance', 'sufficient_funds']

    def sufficient_funds(self, obj):
        return obj.has_sufficient_funds

    sufficient_funds.boolean = True


class SociProductAdmin(admin.ModelAdmin):
    list_display = ['sku_number', 'name', 'price', 'description']

class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['user', 'sum', 'signed_off_time']

    def user(self):
        return self.source.user

    def sum(self):
        return self


admin.site.register(SociBankAccount, SociBankAccountAdmin)
admin.site.register(SociProduct, SociProductAdmin)
