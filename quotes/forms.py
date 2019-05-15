from django import forms

from quotes.models import Quote


class QuoteForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = ('text', 'quoter')

