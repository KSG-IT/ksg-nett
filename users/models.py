# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date
import re
from django.utils import timezone
from django.contrib.auth.models import AbstractUser, Permission
from django.conf import settings
from django.db import models
from django.db.models import QuerySet

from common.context_processors import internal_groups
from common.util import get_semester_year_shorthand
from users.managers import UsersHaveMadeOutManager
from organization.models import InternalGroup


class Allergy(models.Model):
    """
    Model containing food preferences and allergies
    """

    name = models.CharField(max_length=32)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    class Meta:
        default_related_name = "allergies"
        verbose_name_plural = "Allergies"


class KnightHood(models.Model):
    """
    Model for knighthood. A knighthood is a special title given to a user
    """

    user = models.OneToOneField(
        "users.User", on_delete=models.CASCADE, related_name="knighthood"
    )
    knighted_date = models.DateField(default=date.today)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"Knighthood for {self.user}"

    def __repr__(self):
        return f"Knighthood(user={self.user})"


class User(AbstractUser):
    nickname = models.CharField(max_length=64, blank=True, null=True, default=None)
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(blank=True, null=True)
    study = models.CharField(default="", blank=True, max_length=100)
    profile_image = models.FileField(upload_to="profiles/", null=True, blank=True)

    phone = models.CharField(default="", blank=True, max_length=50)
    study_address = models.CharField(default="", blank=True, max_length=100)
    home_town = models.CharField(default="", blank=True, max_length=100)

    start_ksg = models.DateField(auto_now_add=True)

    about_me = models.TextField(blank=True, default="", max_length=200)
    in_relationship = models.BooleanField(null=True, default=False)

    allergies = models.ManyToManyField(Allergy, blank=True, related_name="users")
    migrated_from_sg = models.BooleanField(default=False)

    have_made_out_with = models.ManyToManyField(
        "self", through="UsersHaveMadeOut", symmetrical=False
    )
    anonymize_in_made_out_map = models.BooleanField(default=True, null=False)
    sg_id = models.IntegerField(null=True, blank=True)
    requires_migration_wizard = models.BooleanField(default=False)
    first_time_login = models.BooleanField(default=True)
    can_rewrite_about_me = models.BooleanField(default=True)

    ical_token = models.CharField(
        max_length=128, unique=True, null=True, blank=True, default=None
    )
    admission = models.ForeignKey(
        "admissions.Admission",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # Email notification settings
    notify_on_shift = models.BooleanField(default=False)
    notify_on_deposit = models.BooleanField(default=True)
    notify_on_quote = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_full_name()}"

    def __repr__(self):
        return f"User(name={self.get_full_name()})"

    def get_all_permissions(self, obj=None) -> list:
        all_permissions = []
        for user_type in self.user_types.all():
            for app_label, codename in user_type.permissions.values_list(
                "content_type__app_label", "codename"
            ):
                all_permissions.append(*["{}.{}".format(app_label, codename)])

        return all_permissions

    def get_start_ksg_display(self) -> str:
        """
        get_start_ksg_display renders the `start_ksg` attribute into a "semester-year"-representation.
        Examples:
            2018-01-01 => V18
            2014-08-30 => H14
            2012-12-30 => H12
        :return: The "semeter-year" display of the `start_ksg` attribute.
        """
        return get_semester_year_shorthand(self.start_ksg)

    def get_clean_full_name(self):
        """Useful for when you want to display users in a sensible way"""
        return self.get_full_name()

    def get_full_with_nick_name(self):
        """Funny to use in non-serious settings"""
        if self.nickname:
            return f'{self.first_name} "{self.nickname}" {self.last_name}'
        return self.get_full_name()

    @property
    def initials(self):
        full_name = self.get_full_name() or ""

        if len(full_name) < 2:
            full_name = self.username

        if not " " in full_name:
            return full_name[0:2].upper()
        else:
            split = re.split("\W+", full_name)
            first_part, last_part = split[0], split[-1]
            return f"{first_part[0].upper()}{last_part[0].upper()}"

    @property
    def all_having_made_out_with(self) -> QuerySet:
        return self.made_out_with_left_side.all() | self.made_out_with_right_side.all()

    @property
    def future_shifts(self):
        from schedules.models import ShiftSlot

        data = ShiftSlot.objects.filter(
            user=self,
            shift__datetime_end__gt=timezone.now(),
        ).order_by("shift__datetime_start")
        return data

    @property
    def ksg_status(self):
        # ToDo Rework this shit. Doesn't make sense
        return (
            self.internal_group_position_history.filter(date_ended__isnull=True)
            .first()
            .position
            if self.internal_group_position_history.filter(
                date_ended__isnull=True
            ).first()
            else None
        )

    @property
    def balance(self) -> int:
        return self.bank_account.balance

    @property
    def last_transactions(self):
        return self.bank_account.transaction_history[:10]

    @property
    def current_internal_group_position_membership(self):
        return self.internal_group_position_history.filter(
            position__internal_group__type=InternalGroup.Type.INTERNAL_GROUP,
            date_ended__isnull=True,
        ).first()

    @property
    def get_invited_soci_order_session(self):
        from economy.models import SociOrderSession

        active_session = SociOrderSession.get_active_session()
        if not active_session:
            return
        if active_session.invited_users.filter(pk=self.pk).exists():
            return active_session

    @property
    def owes_money(self) -> bool:
        if self.is_superuser:
            return False
        account = self.bank_account
        return account.balance < settings.OWES_MONEY_THRESHOLD

    @property
    def active_internal_group_position(self):
        membership = self.internal_group_position_history.filter(
            date_ended__isnull=True,
            position__internal_group__type=InternalGroup.Type.INTERNAL_GROUP,
        )
        if membership.exists():
            return membership.first().position

        return None

    @property
    def is_at_work(self):
        return self.filled_shifts.filter(
            shift__datetime_start__lte=timezone.now(),
            shift__datetime_end__gte=timezone.now(),
        ).exists()


class UsersHaveMadeOut(models.Model):
    """
    UsersHaveMadeOut is a model representing a pair of users having made out. We model this with an
    explicit model to associate extra data to it.
    """

    user_one = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="made_out_with_left_side"
    )
    user_two = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="made_out_with_right_side"
    )

    objects = UsersHaveMadeOutManager()

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user_one", "user_two"]),
            models.Index(fields=["user_two", "user_one"]),
        ]

    def __str__(self):
        return f"User {self.user_one.get_full_name()} have made out with {self.user_two.get_full_name()}"

    def __repr__(self):
        return f"UsersHaveMadeOut(user_one={self.user_one.id}, user_two={self.user_two.id})"


class UserTypeLogEntry(models.Model):
    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "User type log entries"

    class Action(models.TextChoices):
        ADD = ("ADD", "Add")
        REMOVE = ("REMOVE", "Remove")

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_type_log"
    )
    user_type = models.ForeignKey(
        "users.UserType", on_delete=models.CASCADE, related_name="changelog"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    done_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_type_log_entries"
    )
    action = models.CharField(max_length=10, choices=Action.choices)

    def __str__(self):
        return f"{self.user_type} for {self.user}"

    def __repr__(self):
        return f"UserTypeLogEntry(user_type={self.user_type}, user={self.user})"


class UserType(models.Model):
    class Meta:
        ordering = ["name"]
        verbose_name_plural = "User types"

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    permissions = models.ManyToManyField(
        Permission, blank=True, help_text="The permissions this user type grants."
    )
    users = models.ManyToManyField(
        User,
        related_name="user_types",
        help_text="The users having this user type.",
    )
    requires_superuser = models.BooleanField(
        default=False,
        help_text="Whether this user type requires a superuser to be granted to another user.",
    )
    requires_self = models.BooleanField(
        default=False,
        help_text="Whether this user type requires to have the permissions of the user type to grant them to another "
        "user.",
    )

    def __str__(self):
        return f"UserType {self.name}"

    def __repr__(self):
        return f"UserType(name={self.name})"
