# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import AbstractUser
from django.db import models

# KSG choices
from commissions.models import Commission

KSG_STATUS_TYPES = (
    ("aktiv", "Aktiv"),  # Wants to stay in KSG
    ("inaktiv", "Ikke aktiv"),  # Finished with KSG duties, but want to leave
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

# Allergy types
ALLERGIES = (
    ("gluten", "Glutenallergi"),
    ("lactose", "Laktoseintolerant"),
    ("milk", "Melkeallergi"),
    ("nuts", "Nøtter"),
    ("shellfish", "Skalldyr"),
    ("celery", "Selleri"),
    ("soy", "Soya"),
    ("fish", "Fisk"),
    ("egg", "Egg"),
)


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
        default_related_name = 'allergies'
        verbose_name_plural = 'Allergies'


class User(AbstractUser):
    """
    A KSG user
    """
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(blank=True, null=True)
    study = models.CharField(default="", blank=True, max_length=100)
    profile_image = models.FileField(upload_to='profiles/', null=True, blank=True)
    serious_profile_image = models.FileField(upload_to='profiles', null=True, blank=True)
    in_relationship = models.BooleanField(default=False)
    biography = models.TextField(blank=True, default="", max_length=200)

    phone = models.CharField(default="", blank=True, max_length=50)
    study_address = models.CharField(default="", blank=True, max_length=100)
    home_address = models.CharField(default="", blank=True, max_length=100)

    start_ksg = models.DateField(auto_now_add=True)
    ksg_status = models.CharField(max_length=32, choices=KSG_STATUS_TYPES, default=KSG_STATUS_TYPES[0])
    ksg_role = models.CharField(max_length=32, choices=KSG_ROLES, default=KSG_ROLES[0])
    

    commission = models.ForeignKey(
        Commission,
        default=None,
        blank=True,
        null=True,
        related_name='holders',
        on_delete=models.SET_NULL
    )

    allergies = models.ManyToManyField(
        Allergy,
        blank=True,
        related_name='users'
    )

    def __str__(self):
        return f"User {self.get_full_name()}"

    def __repr__(self):
        return f"User(name={self.get_full_name()})"

    @property
    def current_commission(self):
        return f"{self.commission.name}" if self.commission else None

    def active(self):
        return self.ksg_status == KSG_STATUS_TYPES[0][0]

    active.boolean = True

    class Meta:
        default_related_name = 'users'
        verbose_name_plural = 'Users'




