from django.conf.urls import include
from django.urls import path, re_path

from . import views

urlpatterns = [
    re_path(r'^$', views.index),
    path('quotes/', include('quotes.urls')),
    path('summaries/', include('summaries.urls')),
    path('users/', include('users.urls')),
    path('chat/', include('chat.urls')),
    path('economy/', include('economy.urls')),
    path('quiz/', include('quiz.urls')),
    # Catch all internal views not otherwise matched in a custom 404
    re_path('', views.not_found)
]
