from django.conf.urls import include
from django.urls import path, re_path

from . import views

urlpatterns = [
    path('deposit', views.deposit_view, )
]