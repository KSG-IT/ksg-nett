from django import forms

from quotes.models import Quote


class QuoteForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = ('text', 'tagged', 'context')

    # This adds the mentioned css class to the related field widget which allows for more custom styling.
    # Can accept several classes separated with space
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].widget.attrs.update({'class': 'default-text-area'})
