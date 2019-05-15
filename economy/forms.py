from django import forms
from economy.models import Deposit


class DepositForm(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = ('amount', 'receipt', 'description', 'account')
       # exclude = ('account',)
