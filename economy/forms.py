from django import forms
from economy.models import Deposit, DepositComment, ProductOrder


class DepositForm(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = ('amount', 'receipt', 'description')


class DepositCommentForm(forms.ModelForm):
    class Meta:
        model = DepositComment
        fields = ('comment',)


class ProductOrderForm(forms.ModelForm):
    class Meta:
        model = ProductOrder
        fields = ("source", "product", "order_size",)
