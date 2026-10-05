# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.db.models import Count
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
    search_fields = ["name"]


class KnightHoodAdmin(admin.ModelAdmin):
    model = KnightHood
    verbose_name = "Knighthood"
    verbose_name_plural = "Knighthoods"
    list_display = ["user", "knighted_date"]
    list_select_related = ["user"]
    search_fields = ["user__first_name", "user__last_name", "description"]
    autocomplete_fields = ["user"]


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
    list_display = ["pk", "full_name", "username", "email", "is_active", "is_staff"]
    list_filter = ["is_active", "is_staff", "is_superuser", "user_types"]
    search_fields = [
        "username",
        "first_name",
        "last_name",
        "nickname",
        "email",
        "phone",
    ]
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

    @admin.display(ordering="first_name")
    def full_name(self, obj):
        return obj.get_full_name()


class UsersHaveMadeOutAdmin(admin.ModelAdmin):
    readonly_fields = ("created",)
    list_display = (
        "user_one",
        "user_two",
        "created",
    )
    list_select_related = ("user_one", "user_two")
    search_fields = (
        "user_one__first_name",
        "user_one__last_name",
        "user_two__first_name",
        "user_two__last_name",
    )
    autocomplete_fields = ("user_one", "user_two")


class UserTypeAdmin(admin.ModelAdmin):
    filter_horizontal = ("users", "permissions")
    list_display = (
        "name",
        "user_count",
        "requires_self",
        "requires_superuser",
    )
    search_fields = ("name", "description")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(user_count=Count("users"))

    @admin.display(description="Users", ordering="user_count")
    def user_count(self, user_type):
        return user_type.user_count

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # Permission.__str__ renders its content type
        if db_field.name == "permissions":
            kwargs["queryset"] = db_field.remote_field.model.objects.select_related(
                "content_type"
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)


class UserTypeLogEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "user_type", "action", "done_by", "timestamp")
    list_select_related = ("user", "user_type", "done_by")
    list_filter = ("action", "user_type")
    search_fields = (
        "user__first_name",
        "user__last_name",
        "done_by__first_name",
        "done_by__last_name",
    )
    date_hierarchy = "timestamp"
    autocomplete_fields = ("user", "done_by")


admin.site.register(User, MyUserAdmin)
admin.site.register(Allergy, AllergyAdmin)
admin.site.register(KnightHood, KnightHoodAdmin)
admin.site.register(UsersHaveMadeOut, UsersHaveMadeOutAdmin)
admin.site.register(UserType, UserTypeAdmin)
admin.site.register(UserTypeLogEntry, UserTypeLogEntryAdmin)
