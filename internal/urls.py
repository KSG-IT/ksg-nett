from django.urls import re_path, path, include

from . import views

urlpatterns = [
    re_path(r'^$', views.index),
    path('quotes/', include('quotes.urls')),
    path('summaries/', include('summaries.urls')),
]
