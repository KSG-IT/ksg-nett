# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from economy.models import SociBankAccount
from users.models import (
    KnightHood,
    User,
    Allergy,
    UsersHaveMadeOut,
    UserType,
    UserTypeLogEntry,
)


class MyUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


class MyUserCreationForm(UserCreationForm):
    email = forms.EmailField(label=_("E-mail"))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "email",
        )


class AllergyAdmin(admin.ModelAdmin):
    list_display = ["pk", "name"]


class KnightHoodAdmin(admin.ModelAdmin):
    model = KnightHood
    verbose_name = "Knighthood"
    verbose_name_plural = "Knighthoods"


class UserTypeInline(admin.TabularInline):
    fk_name = "user"
    model = UserType.users.through
    extra = 0
    verbose_name = "User type"
    verbose_name_plural = "User types"


class SociBankAccountInline(admin.StackedInline):
    model = SociBankAccount
    fields = ["card_uuid"]
    verbose_name = "Soci Bank Account"
    verbose_name_plural = "Soci Bank Accounts"
    can_delete = False


class MyUserAdmin(UserAdmin):
    list_display = ["pk", "full_name", "is_active"]
    form = MyUserChangeForm
    filter_horizontal = ("allergies",)
    add_form = MyUserCreationForm
    fieldsets = UserAdmin.fieldsets + (
        (
            "Personalia",
            {
                "fields": (
                    "date_of_birth",
                    "study",
                )
            },
        ),
        (
            "Notifications",
            {
                "fields": (
                    "notify_on_deposit",
                    "notify_on_quote",
                    "notify_on_shift",
                )
            },
        ),
        (
            "Contact",
            {
                "fields": (
                    "phone",
                    "study_address",
                    "home_town",
                )
            },
        ),
        ("Media", {"fields": ("profile_image",)}),
        (
            "Additional info",
            {
                "fields": (
                    "about_me",
                    "nickname",
                    "in_relationship",
                    "allergies",
                    "anonymize_in_made_out_map",
                    "requires_migration_wizard",
                    "first_time_login",
                    "can_rewrite_about_me",
                    "sg_id",
                    "ical_token",
                )
            },
        ),
    )
    inlines = [SociBankAccountInline, UserTypeInline]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
    )

    @staticmethod
    def full_name(obj):
        return obj.get_full_name()


class UsersHaveMadeOutAdmin(admin.ModelAdmin):
    readonly_fields = ("created",)
    list_display = (
        "user_one",
        "user_two",
        "created",
    )


class UserTypeAdmin(admin.ModelAdmin):
    filter_horizontal = ("users", "permissions")
    list_display = (
        "name",
        "requires_self",
        "requires_superuser",
    )


class UserTypeLogEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "user_type", "action", "done_by")


admin.site.register(User, MyUserAdmin)
admin.site.register(Allergy, AllergyAdmin)
admin.site.register(KnightHood, KnightHoodAdmin)
admin.site.register(UsersHaveMadeOut, UsersHaveMadeOutAdmin)
admin.site.register(UserType, UserTypeAdmin)
admin.site.register(UserTypeLogEntry, UserTypeLogEntryAdmin)
