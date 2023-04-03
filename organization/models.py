# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from typing import Optional

from django.db import models
from django.utils import timezone
from organization.consts import InternalGroupPositionMembershipType
from django.utils.translation import gettext_lazy as _
from common.util import get_semester_year_shorthand


class InternalGroup(models.Model):
    class Meta:
        default_related_name = "groups"
        verbose_name_plural = "Internal groups"

    class Type(models.TextChoices):
        """
        Making use of https://docs.djangoproject.com/en/3.1/ref/models/fields/#enumeration-types
        Denotes the internal group type, either a interest-group, e.g. KSG-iT, Påfyll etc. or an internal
        grouping, e.g. Lyche bar og Edgar
        """

        INTEREST_GROUP = "interest-group", _("Interest group")
        INTERNAL_GROUP = "internal-group", _("Internal group")

    name = models.CharField(unique=True, max_length=32)
    type = models.CharField(
        max_length=32, null=False, blank=False, choices=Type.choices
    )
    description = models.TextField(max_length=2048, blank=True, null=True)
    group_image = models.ImageField(upload_to="internalgroups", null=True, blank=True)
    group_icon = models.ImageField(upload_to="internalgroups", null=True, blank=True)
    highlighted_name = models.CharField(
        max_length=32, default="Funksjonærene", null=False
    )

    @property
    def active_members(self):
        """
        Returns all group positions membership with a FK to positions with a FK to this instance. Returns
        only "active" memberships which is defined as memberships without an ending date
        """
        group_members = []
        for position in self.positions.all():
            group_members.extend(position.active_memberships.all())

        group_members.sort(key=lambda x: x.user.get_full_name())
        return group_members

    @property
    def active_members_count(self) -> int:
        return len(self.active_members)

    @classmethod
    def get_internal_groups(cls):
        return cls.objects.filter(type=cls.Type.INTERNAL_GROUP.value).order_by("name")

    @classmethod
    def get_interest_groups(cls):
        return cls.objects.filter(type=cls.Type.INTEREST_GROUP.value).order_by("name")

    def __str__(self):
        return "Group %s" % self.name

    def __repr__(self):
        return "Group(name=%s)" % self.name


class InternalGroupPositionMembership(models.Model):
    """
    An intermediary model between a user and a InternalGroupPosition with additional information
    regarding membership
    """

    date_joined = models.DateField(default=timezone.now, null=False, blank=False)
    date_ended = models.DateField(default=None, null=True, blank=True)
    type = models.CharField(
        max_length=32,
        choices=InternalGroupPositionMembershipType.choices,
        null=False,
        blank=False,
    )

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="internal_group_position_history",
    )
    position = models.ForeignKey(
        "organization.InternalGroupPosition",
        related_name="memberships",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return (
            f"{self.user}: {self.position.name} {self.type} from "
            f"{get_semester_year_shorthand(self.date_joined)} to "
            f"{get_semester_year_shorthand(self.date_ended)}"
        )

    def get_semester_of_membership(self, start) -> str:
        if start:
            short_year_format = str(self.date_joined.year)[2:]
            semester_prefix = "H" if self.date_joined.month > 7 else "V"
        elif not start and self.date_ended:
            short_year_format = str(self.date_ended.year)[2:]
            semester_prefix = "H" if self.date_ended.month > 7 else "V"
        else:
            return ""
        return f"{semester_prefix}{short_year_format}"


class InternalGroupPosition(models.Model):
    """
    A position for an internal group, e.g. Hovmester
    """

    class Meta:
        unique_together = ("name", "internal_group")

    name = models.CharField(max_length=32)
    # We mark if this position is usually available to external applicants
    available_externally = models.BooleanField(default=False)
    internal_group = models.ForeignKey(
        InternalGroup,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="positions",
    )
    description = models.CharField(max_length=1024, blank=True, null=True)

    holders = models.ManyToManyField(
        "users.User",
        related_name="positions",
        through="organization.InternalGroupPositionMembership",
    )

    @classmethod
    def get_externally_available_positions(cls):
        return cls.objects.filter(available_externally=True).order_by("name")

    @property
    def active_memberships(self):
        return self.memberships.filter(date_ended__isnull=True)

    @property
    def active_memberships_count(self) -> int:
        return self.active_memberships.count()

    def __str__(self):
        return f"{self.internal_group.name}: {self.name}"


class InternalGroupUserHighlight(models.Model):
    """
    A model for highlighting a user in an internal group
    """

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="internal_group_highlights"
    )
    internal_group = models.ForeignKey(
        InternalGroup,
        on_delete=models.CASCADE,
        related_name="user_highlights",
    )
    occupation = models.CharField(max_length=32, null=False, blank=True, default="")
    description = models.TextField(max_length=1024, blank=True, null=True)
    image = models.ImageField(upload_to="internalgroups", null=True, blank=True)
    archived = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name()}"
