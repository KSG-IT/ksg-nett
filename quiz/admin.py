from django.contrib import admin
from users.models import User
# Register your models here.

from django.contrib import admin
from .models import Quiz

admin.site.register(Quiz)