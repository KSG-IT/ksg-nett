from django import forms

from organization.models import InternalGroup


class InternalGroupForm(forms.ModelForm):
    class Meta:
        model = InternalGroup
        fields = ("group_image", "description")

    # This adds the mentioned css class to the related field widget which allows for more custom styling.
    # Can accept several classes separated with space
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].widget.attrs.update({"class": "default-text-area"})
