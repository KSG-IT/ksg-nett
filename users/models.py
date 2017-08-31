# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils import timezone


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

	status_KSG = models.CharField(max_length=4, choices=KSG_STATUS_TYPES)
	start_KSG = models.DateField.auto_now_add(default=timezone.now())

	image = FileField()  # (upload_to='uploads')
