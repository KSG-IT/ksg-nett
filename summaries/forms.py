from django import forms

from summaries.models import Summary


class SummaryForm(forms.ModelForm):
    class Meta:
        model = Summary
        fields = (
            'summary_type', 'contents', 'participants', 'reporter', 'date'
        )
