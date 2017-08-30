# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils import timezone

# Create your models here.

class Person(models.Model):
	name = models.CharField(max_length=100)
	email = models.EmailField()
	phone = 
	study = 
	date_of_birth = models.DateField()
	
	study_address = model.TextField(max_length=100)
	home_address = model.TextField(max_length=100)
	
	status_KSG = 
	start_KSG = model.DateField.auto_now_add(default=timezone.now())
	
	image = FileField()#(upload_to='uploads')