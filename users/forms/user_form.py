from django import forms
from users.models import User
from economy.models import SociBankAccount


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = {
            'first_name', 'last_name', 'phone', 'study', 'biography', 'email', 'profile_image'
        }
