from django import forms
from economy.models import Deposit, DepositComment, ProductOrder
from bar_tab.models import BarTabCustomer


class DepositForm(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = ("amount", "receipt", "description")


class DepositCommentForm(forms.ModelForm):
    class Meta:
        model = DepositComment
        fields = ("comment",)


class ProductOrderForm(forms.ModelForm):
    class Meta:
        model = ProductOrder
        fields = (
            "source",
            "product",
            "order_size",
        )


class ExternalChargeForm(forms.Form):
    amount = forms.IntegerField(label="Beløp", min_value=1, max_value=300, initial=1)
    bar_tab_customer = forms.ModelChoiceField(
        queryset=BarTabCustomer.objects.all().order_by("name"),
        label="Hybel som krysser",
    )
    reference = forms.CharField(required=False, label="Referanse (valgfritt)")

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get("amount")
        bar_tab_customer = cleaned_data.get("bar_tab_customer")
        if not bar_tab_customer:
            raise forms.ValidationError("Du må velge en gjeng")
        if not amount:
            raise forms.ValidationError("Du må velge et beløp")
        return cleaned_data
