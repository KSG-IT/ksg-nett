from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.summaries_list),
    url(r'^create', views.summaries_create, name='summaries_create'),
]
