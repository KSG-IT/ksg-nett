# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(blank=True, null=True)
    study = models.CharField(default="", blank=True, max_length=100)
    profile_image = models.FileField(upload_to='profiles/', null=True)

    phone = models.CharField(default="", blank=True, max_length=50)
    study_address = models.CharField(default="", blank=True, max_length=100)
    home_address = models.CharField(default="", blank=True, max_length=100)

    start_ksg = models.DateField(auto_now_add=True)

    def __str__(self):
        return "User %s" % (self.first_name,)

    def __repr__(self):
        return "User(name=%s)" % (self.first_name,)

    class Meta:
        default_related_name = 'users'
        verbose_name_plural = 'Users'
