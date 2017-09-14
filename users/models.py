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
    profile_image = models.FileField(upload_to='profiles/', blank=True, null=True)

    # Contact information
    email = models.EmailField(max_length=50)
    phone = models.CharField(max_length=50)
    study_address = models.CharField(max_length=100)
    home_address = models.CharField(max_length=100)

    # KSG activity (
    #current_status_ksg = models.ForeignKey()   # This should come from a user group relation model
    #current_ksg_role = models.ForeignKey()     # This should come from a user group relation model
    #ksg_history = models.OneToOneField()       # This should be calculated from user group relations
    start_ksg = models.DateField(auto_now_add=True)

    def __str__(self):
        return "UserProfile for %s" % (self.name,)

    def __repr__(self):
        return "UserProfile(name=%s, user=%d)" % (self.name, self.user.id)

    class Meta:
        default_related_name = 'user_profiles'
        verbose_name_plural = 'UserProfiles'
