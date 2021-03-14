from django.urls import path

from . import views

app_name = 'quiz'
urlpatterns = [
    path('', views.index, name='index'),
]