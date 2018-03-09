from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.summaries_list),
    url(r'^create', views.summaries_create, name='summaries_create'),
    url(r'(?P<summary_id>[0-9]+)/update', views.summaries_update, name='summaries_update'),
    url(r'(?P<summary_id>[0-9]+)/delete', views.summaries_delete, name='summaries_delete'),
]
