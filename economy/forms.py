from django import forms
from economy.models import Deposit, DepositComment, SociProduct, ProductOrder

class DepositForm(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = ('amount', 'receipt', 'description')


class DepositCommentForm(forms.ModelForm):
    class Meta:
        model = DepositComment
        fields = ('comment',)


class SociProductForm(forms.ModelForm):
    class Meta:
        model = SociProduct
        fields = ("sku_number", "name", "price", "description", "icon")


class ProductOrderForm(forms.ModelForm):
    class Meta:
        model = ProductOrder
        fields = ("source", "order_size", "product")
