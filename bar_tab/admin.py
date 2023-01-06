from django.contrib import admin
from .models import BarTab, BarTabCustomer, BarTabOrder, BarTabProduct, BarTabInvoice


class BarTabAdmin(admin.ModelAdmin):
    pass


admin.site.register(BarTab, BarTabAdmin)
admin.site.register(BarTabCustomer)
admin.site.register(BarTabOrder)
admin.site.register(BarTabProduct)
admin.site.register(BarTabInvoice)
