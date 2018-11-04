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


class User(AbstractUser):
    """
    A KSG user
    """
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(blank=True, null=True)
    study = models.CharField(default="", blank=True, max_length=100)
    profile_image = models.FileField(upload_to='profiles/', null=True)

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

    def __str__(self):
        return f"User {self.get_full_name()}"

    def __repr__(self):
        return f"User(name={self.get_full_name()})"

    @property
    def current_commission(self):
        return f"{self.commission.name}" if self.commission else None

    def active(self):
        return self.ksg_status == KSG_STATUS_TYPES[0][0]

    def get_start_ksg_display(self):
        """
        This method returns a "semester-year" display for the start ksg date.
        Examples:
            2018-01-01 => V18
            2014-08-30 => H14
            2012-12-30 => H12
        :return:
        """
        short_year_format = str(self.start_ksg.year)[2:]
        semester_prefix = "H" if self.start_ksg.month > 7 else "V"
        return f"{semester_prefix}{short_year_format}"

    @property
    def profile_image_url(self):
        """
        profile_image_url is a helper property which returns the url of the user's profile
        image, if the user has an associated profile image. The reason this exists, is that
        simply calling `user.profile_image.url` will result in a ValueError if the profile_image
        is null. We can work around this in templates by doing a bunch of if-conditionals. However,
        it is more practical to use the `default_if_none` filter, hence this method returns None if the
        image does not exist.
        :return:
        """
        if self.profile_image and hasattr(self.profile_image, 'url'):
            return self.profile_image.url
        return None

    active.boolean = True

    class Meta:
        default_related_name = 'users'
        verbose_name_plural = 'Users'
