# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models


# Create your models here.
class Group(models.Model):
    name = models.CharField(max_length=255)

    members = models.ManyToManyField(
        User,
        blank=True,
        related_name='internal_groups'  # The default django user model already has a `groups` related_name
                                        # so we have to make a custom one
    )

    def __str__(self):
        return "Group %s" % self.name

    def __repr__(self):
        return "Group(name=%s)" % self.name

    class Meta:
        default_related_name = 'groups'
        verbose_name_plural = 'Groups'
