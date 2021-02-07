from django import forms

from organization.models import InternalGroup


class InternalGroupForm(forms.ModelForm):
    class Meta:
        model = InternalGroup
        fields = ("group_image", "description")
