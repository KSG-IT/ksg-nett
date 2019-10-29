from django import forms
from users.models import User


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = {
            'first_name', 'last_name', 'phone', 'study', 'biography', 'email', 'profile_image', 'study_address',
            'home_address', 'commission', 'ksg_status', 'in_relationship'
        }
