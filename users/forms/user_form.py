from django import forms
from users.models import User


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = {
            'first_name', 'last_name', 'phone', 'study', 'biography'
        }


class UserFormAdmin(UserForm):
    class Meta:
        model = User
        fields = {
            'in_relationship'
        }
