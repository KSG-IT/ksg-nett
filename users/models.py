# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
from typing import Optional
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import QuerySet
from model_utils.models import TimeStampedModel

from common.util import get_semester_year_shorthand
from users.managers import UsersHaveMadeOutManager
from organization.consts import InternalGroupPositionType


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


class User(AbstractUser):
    """
    A KSG user
    """

    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(blank=True, null=True)
    study = models.CharField(default="", blank=True, max_length=100)
    profile_image = models.FileField(upload_to="profiles/", null=True, blank=True)

    phone = models.CharField(default="", blank=True, max_length=50)
    study_address = models.CharField(default="", blank=True, max_length=100)
    home_address = models.CharField(default="", blank=True, max_length=100)

    start_ksg = models.DateField(auto_now_add=True)

    biography = models.TextField(blank=True, default="", max_length=200)
    in_relationship = models.BooleanField(null=True, default=False)

    allergies = models.ManyToManyField(Allergy, blank=True, related_name="users")

    have_made_out_with = models.ManyToManyField(
        "self", through="UsersHaveMadeOut", symmetrical=False
    )
    anonymize_in_made_out_map = models.BooleanField(default=True, null=False)

    def __str__(self):
        return f"User {self.get_full_name()}"

    def __repr__(self):
        return f"User(name={self.get_full_name()})"

    @property
    def current_commission(self):
        return (
            f"{self.commission_history.filter(date_ended__isnull=False).first().name}"
            if self.commission_history.filter(date_ended__isnull=False).first()
            else None
        )

    @property
    def active(self):
        return self.ksg_status in [
            InternalGroupPositionType.ACTIVE_FUNCTIONARY_PANG.value,
            InternalGroupPositionType.ACTIVE_GANG_MEMBER_PANG.value,
            InternalGroupPositionType.FUNCTIONARY.value,
            InternalGroupPositionType.GANG_MEMBER.value,
            InternalGroupPositionType.HANGAROUND.value,
        ]

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

    @property
    def profile_image_url(self) -> Optional[str]:
        """
        profile_image_url is a helper property which returns the url of the user's profile
        image, if the user has an associated profile image. The reason this exists, is that
        simply calling `user.profile_image.url` will result in a ValueError if the profile_image
        is null. We can work around this in templates by doing a bunch of if-conditionals. However,
        it is more practical to use the `default_if_none` filter, hence this method returns None if the
        image does not exist.
        :return: The url of the `profile_image` attribute, if it exists, otherwise None.
        """
        if self.profile_image and hasattr(self.profile_image, "url"):
            return self.profile_image.url
        return None

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
        return self.shift_set.filter(slot__group__meet_time__gte=timezone.now())

    @property
    def ksg_status(self):
        return (
            self.internal_group_position_history.filter(date_ended__isnull=True)
            .first()
            .position.type
            if self.internal_group_position_history.filter(
                date_ended__isnull=True
            ).first()
            else None
        )

    class Meta:
        default_related_name = "users"
        verbose_name_plural = "Users"


class UsersHaveMadeOut(TimeStampedModel):
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

    class Meta:
        indexes = [
            models.Index(fields=["user_one", "user_two"]),
            models.Index(fields=["user_two", "user_one"]),
        ]

    def __str__(self):
        return f"User {self.user_one.get_full_name()} have made out with {self.user_two.get_full_name()}"

    def __repr__(self):
        return f"UsersHaveMadeOut(user_one={self.user_one.id}, user_two={self.user_two.id})"
