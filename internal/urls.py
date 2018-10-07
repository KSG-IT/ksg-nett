from django.conf.urls import include
from django.urls import path, re_path

from . import views

urlpatterns = [
    re_path(r'^$', views.index),
    path('quotes/', include('quotes.urls')),
    path('summaries/', include('summaries.urls')),
]
