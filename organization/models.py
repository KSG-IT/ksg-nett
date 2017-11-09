# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.
from users.models import User


# Internal groups in KSG
KSG_INTERNAL_GROUPS = (
    ("arrangement", "Arrangement"),
    ("bar", "Bargjengen"),
    ("bryggeriet", "Daglighallen mikrobryggeri"),
    ("daglighallen", "Daglighallen"),
    ("edgar", "Edgar"),
    ("lychebar", "Lyche Bar"),
    ("lychekjokken", "Lyche Kjøkken"),
    ("sprit", "Spritgjengen"),
    ("styret", "Styret"),
    ("okonomi", "Økonomi"),
)

# Positions that can be held while in KSG
# Note: Should only be available if you are aktiv
KSG_POSITIONS = (
    # Arrangement
    ("arrangementsansvarlig", "Arrangementsansvarlig"),
    ("arrangementsbartender", "Arrangementsbartender"),
    # Bargjengen
    ("barsjef", "Barsjef"),
    ("bartender", "Bartender"),
    # Bryggeriet
    ("bryggfunk", "Bryggfunk"),
    ("brygger", "Brygger"),
    # Daglighallen
    ("daglighallenfunk", "Daglighallenfunk"),
    ("daglighallenfunk", "Daglighallenbartender"),
    # Edgar
    ("kafeansvarlig", "Kaféansvarlig"),
    ("baristaer", "Barista"),
    # Lyche bar
    ("hovmester", "Hovmester"),
    ("barservitor", "Barservitør"),
    # Lyche kjøkken
    ("souschef", "Souschef"),
    ("kokk", "Kokk"),
    # Spritgjengen
    ("spritbarsjef", "Spritbarsjef"),
    ("spritbartender", "Spritbartender"),
    # Styret
    ("styret", "Styret"),
    # Økonomi
    ("okonomi", "Økonomi"),
)


class InternalGroup(models.Model):
    """
    An internal group within KSG, e.g. Lyche bar
    """
    name = models.CharField(max_length=32, choices=KSG_INTERNAL_GROUPS)

    description = models.CharField(max_length=1024)

    members = models.ManyToManyField(
        User,
        blank=True,
        related_name='internal_group'  # The default django user model already has a `groups` related_name
        # so we have to make a custom one
    )

    def __str__(self):
        return "Group %s" % self.name

    def __repr__(self):
        return "Group(name=%s)" % self.name

    class Meta:
        default_related_name = 'groups'
        verbose_name_plural = 'Groups'
