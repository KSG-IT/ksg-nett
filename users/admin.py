# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import ugettext_lazy as _

from economy.models import SociBankAccount
from users.models import User


class MyUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


class MyUserCreationForm(UserCreationForm):
    email = forms.EmailField(label=_('E-mail'))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email',)


class SociBankAccountInline(admin.StackedInline):
    model = SociBankAccount
    fields = ['card_uuid', 'balance', 'display_balance_at_soci']
    verbose_name_plural = 'Soci Bank Account'
    can_delete = False


class MyUserAdmin(UserAdmin):
    list_display = ['pk', 'full_name', 'ksg_role', 'current_commission', 'active']
    form = MyUserChangeForm
    add_form = MyUserCreationForm
    fieldsets = UserAdmin.fieldsets + (
        ('Personalia', {'fields': ('date_of_birth', 'study',)}),
        ('Contact', {'fields': ('phone', 'study_address', 'home_address',)}),
        ('KSG options', {'fields': ('ksg_status', 'ksg_role', 'commission',)}),
    )
    inlines = [SociBankAccountInline]
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )

    @staticmethod
    def full_name(obj):
        return obj.get_full_name()


admin.site.register(User, MyUserAdmin)
