from django import forms


class UserForm(forms.Form):
    your_number = forms.CharField(label='your_number', max_length=20)
