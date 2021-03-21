from django import forms
from users.models import User
from django.utils.translation import gettext_lazy as _


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = {
            'first_name', 'last_name', 'phone', 'study', 'biography', 'email', 'study_address',
            'home_address', 'in_relationship'
        }
        labels = {
            'first_name': _('First name'),
            'last_name': _('Last name'),
            'phone': _('Phone'),
            'study': _('Field of study'),
            'biography': _('Biography'),
            'email': _('Email'),
            'study_address': _('Study address'),
            'home_address': _('Home address'),
            'in_relationship': _('In relationship')
        }
