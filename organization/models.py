# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from users.models import User


class InternalGroup(models.Model):
    class Meta:
        default_related_name = 'groups'
        verbose_name_plural = 'Internal groups'

    class Type(models.TextChoices):
        """
        Making use of https://docs.djangoproject.com/en/3.1/ref/models/fields/#enumeration-types
        Denotes the internal group type, either a interest-group, e.g. KSG-iT, Påfyll etc. or an internal
        grouping, e.g. Lyche bar og Edgar
        """
        INTEREST_GROUP = "interest-group"
        INTERNAL_GROUP = "internal-group"

    name = models.CharField(unique=True, max_length=32)
    type = models.CharField(max_length=32, null=False, blank=False, choices=Type.choices)
    description = models.TextField(max_length=2048, blank=True, null=True)

    @property  # consider this not being a property seeing as its more "computationally" expensive than normal properties?
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

    def __str__(self):
        return "Group %s" % self.name

    def __repr__(self):
        return "Group(name=%s)" % self.name


class InternalGroupPositionMembership(models.Model):
    """
    An intermediary model between a user and a InternalGroupPosition with additional information
    regarding membership
    """
    date_joined = models.DateField(auto_now_add=True)
    date_ended = models.DateField(
        default=None,
        null=True,
        blank=True
    )

    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    position = models.ForeignKey("organization.InternalGroupPosition", related_name="memberships",
                                 on_delete=models.CASCADE)


class InternalGroupPosition(models.Model):
    """
    A position for an internal group, e.g. Hovmester
    """

    class Meta:
        unique_together = ("name", "internal_group", "type")

    class Type(models.TextChoices):
        FUNCTIONARY = "functionary"
        GANG_MEMBER = "gang-member"
        INTEREST_GROUP_MEMBER = "interest-group-member"
        ACTIVE_FUNCTIONARY_PANG = "active-functionary-pang"
        OLD_FUNCTIONARY_PANG = "old-functionary-pang"
        ACTIVE_GANG_MEMBER_PANG = "active-gang-member-pang"
        OLD_GANG_MEMBER_PANG = "old-gang-member-pang"
        HANGAROUND = "hangaround"

    name = models.CharField(unique=True, max_length=32)
    internal_group = models.ForeignKey(InternalGroup, null=False, blank=False, on_delete=models.CASCADE,
                                       related_name="positions")
    description = models.CharField(max_length=1024, blank=True, null=True)
    type = models.CharField(max_length=32, choices=Type.choices, null=False, blank=False)
    holders = models.ManyToManyField(
        User,
        related_name='positions',
        through="organization.InternalGroupPositionMembership"
    )

    @property
    def active_memberships(self):
        return self.memberships.filter(date_ended__isnull=True)

    @property
    def active_memberships_count(self) -> int:
        return self.active_memberships.count()

    def __str__(self):
        return "Position %s" % self.name

    def __repr__(self):
        return "Position(name=%s)" % self.name


class Commission(models.Model):
    """
    A commissions (verv) in KSG. A commissions can be shared by many users (e.g. Personal),
    or created specifically for this internal group (e.g. Hybelbarsjef).
    """

    name = models.CharField(max_length=32, unique=True)
    holders = models.ManyToManyField(
        User,
        related_name="comissions",
        through="organization.CommissionMembership",
    )

    @property
    def active_holders_count(self):
        return self.memberships.filter(date_ended__isnull=True).count()

    def __str__(self):
        return "Commission %s" % (self.name,)

    def __repr__(self):
        return "Commission(name=%s)" % (self.name,)


class CommissionMembership(models.Model):
    user = models.ForeignKey("users.User", null=False, on_delete=models.CASCADE, related_name="commission_history")
    commission = models.ForeignKey("organization.Commission", on_delete=models.DO_NOTHING, related_name="memberships")
    date_started = models.DateField(auto_now_add=True)
    date_ended = models.DateField(default=None, null=True, blank=True)

    # What happens if a person is personal first semester and is it again their last semester? Just spawn a
    # new instance? Doesnt make sense to extend it, but it feels clunky regardless

    # Add a flag for `in_charge` or something? Does this problem actually need to be solved programaticall


class Committee(models.Model):
    # not sure if this model makes sense whatsoever. Deal with this later

    members = models.ManyToManyField(
        Commission,
        related_name="committees"
    )
