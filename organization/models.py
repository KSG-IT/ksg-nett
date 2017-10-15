# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models


# Create your models here.
from users.models import User


class Group(models.Model):
    name = models.CharField(max_length=255)

    members = models.ManyToManyField(
        User,
        blank=True,
        related_name='internal_groups'  # The default django user model already has a `groups` related_name
                                        # so we have to make a custom one
    )

    # KSG choices
    KSG_STATUS_TYPES = (
        ("aktiv", "Aktiv"),
        ("inaktiv", "Ikke aktiv"),  # Finished with KSG duties
        ("permittert", "Permittert"),  # Implicitly inactive, wants to continue
        ("sluttet", "Sluttet før tiden"),  # Implicitly inactive, has jumped ship
    )

    # Roles in the KSG hierarchy
    KSG_ROLES = (
        ("gjengis", "Gjengis"),
        ("funk", "Funksjonær"),
        ("hangaround", "Hangaround"),
        ("gjengpang", "GjengPang"),
        ("funkepang", "FunkePang"),
        ("hospitant", "Hospitant"),
    )

    def __str__(self):
        return "Group %s" % self.name

    def __repr__(self):
        return "Group(name=%s)" % self.name

    class Meta:
        default_related_name = 'groups'
        verbose_name_plural = 'Groups'
