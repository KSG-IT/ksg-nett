# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils import timezone



KSG_STATUS_TYPES = (
    ('0', 'Aktiv'),
    ('1', 'Funksjonær'),
    ('2', 'junior'),
    ('3', 'senior'),
)

KSG_JOB_TYPES = (
	(),
	(),
	(),
)

class Person(models.Model):
	"""
	Model for a KSG member on KSG-nett
	"""
	# Personal details
	name = models.CharField(max_length=100)
	date_of_birth = models.DateField()
	study = models.CharField(max_length=100)

	# Contact information
	email = models.EmailField(max_length=50)
	phone = models.IntegerField(max_length=8)
	study_address = models.TextField(max_length=100)
	home_address = models.TextField(max_length=100)

	# KSG details

	status_KSG = models.CharField(max_length=4, choices=KSG_STATUS_TYPES)
	start_KSG = models.DateField.auto_now_add(default=timezone.now())
	
	image = FileField()#(upload_to='uploads')