from django.contrib import admin
from users.models import User
# Register your models here.

from django.contrib import admin

from .models import Question
from .models import Choice
from .models import QuizImage

class ImageInline(admin.TabularInline):
    model = QuizImage
    
class UserAdmin(admin.ModelAdmin):
    inlines = [ImageInline]

admin.site.register(QuizImage)
admin.site.register(Question)
admin.site.register(Choice)