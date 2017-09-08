# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    """
    Model for a KSG member on KSG-nett
    """
    user = models.OneToOneField(User, related_name='profile')

    # Personal details
    name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    study = models.CharField(max_length=100)

    # Contact information
    email = models.EmailField(max_length=50)
    phone = models.IntegerField()
    study_address = models.TextField(max_length=100)
    home_address = models.TextField(max_length=100)

    # KSG choices
    KSG_ACTIVITY_TYPES = (
        ("aktiv", "Aktiv"),
        ("inaktiv", "Ikke aktiv"),  # Finished with KSG duties
        ("permittert", "Permittert"),  # Implicitly inactive, wants to continue
        ("sluttet", "Sluttet før tiden"),  # Implicitly inactive, has jumped ship
    )

    KSG_STATUS_TYPES = (
        ("gjengis", "Gjengis"),
        ("funk", "Funksjonær"),
        ("hangaround", "Hangaround"),
        ("gjengpang", "GjengPang"),
        ("funkepang", "FunkePang"),
        ("hospitant", "Hospitant"),
    )

    status_ksg = models.CharField(max_length=32, choices=KSG_STATUS_TYPES)
    start_ksg = models.DateField(auto_now_add=True)

    profile_image = models.FileField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return "UserProfile for %s" % (self.name,)

    def __repr__(self):
        return "UserProfile(name=%s, user=%d)" % (self.name, self.user.id)

    class Meta:
        default_related_name = 'user_profiles'
        verbose_name_plural = 'UserProfiles'
