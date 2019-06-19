from django import forms
from economy.models import Deposit, DepositComment


class DepositForm(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = ('amount', 'receipt', 'description')


class DepositCommentForm(forms.ModelForm):
    class Meta:
        model = DepositComment
        fields = ('comment', 'user', 'deposit')
        exclude = ('user', 'deposit')
