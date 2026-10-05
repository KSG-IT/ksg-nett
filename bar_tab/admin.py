from django.contrib import admin
from .models import BarTab, BarTabCustomer, BarTabOrder, BarTabProduct, BarTabInvoice


class BarTabAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "datetime_opened", "datetime_closed", "created_by"]
    list_select_related = ["created_by"]
    list_filter = ["status"]
    autocomplete_fields = ["created_by", "closed_by", "reviewed_by"]


class BarTabCustomerAdmin(admin.ModelAdmin):
    list_display = ["name", "short_name", "email"]
    search_fields = ["name", "short_name", "email"]


class BarTabOrderAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "bar_tab",
        "customer",
        "type",
        "name",
        "product",
        "quantity",
        "cost",
        "away",
        "reviewed",
    ]
    list_select_related = ["bar_tab", "customer", "product"]
    list_filter = ["type", "away", "reviewed", "customer"]
    search_fields = ["name", "customer__name", "product__name"]


class BarTabProductAdmin(admin.ModelAdmin):
    list_display = ["name", "price"]
    search_fields = ["name"]


class BarTabInvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "bar_tab",
        "customer",
        "amount",
        "datetime_created",
        "datetime_sent",
        "datetime_settled",
    ]
    list_select_related = ["bar_tab", "customer"]
    list_filter = ["customer"]
    search_fields = ["customer__name"]
    autocomplete_fields = ["created_by"]


admin.site.register(BarTab, BarTabAdmin)
admin.site.register(BarTabCustomer, BarTabCustomerAdmin)
admin.site.register(BarTabOrder, BarTabOrderAdmin)
admin.site.register(BarTabProduct, BarTabProductAdmin)
admin.site.register(BarTabInvoice, BarTabInvoiceAdmin)
