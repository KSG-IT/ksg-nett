from django.conf.urls import url
from django.urls import path

from . import views

urlpatterns = [
    url(r'^$', views.summaries_list),
    path('create', views.summaries_create, name='summaries_create'),
    path('search', views.summaries_search, name='summaries_search'),
    path('last', views.summaries_last, name='summaries_last'),
    path('archive', views.summaries_archive, name='summaries_archive'),
    url(r'(?P<summary_id>[0-9]+)/update', views.summaries_update, name='summaries_update'),
    url(r'(?P<summary_id>[0-9]+)/delete', views.summaries_delete, name='summaries_delete'),
    url(r'(?P<summary_id>[0-9]+)', views.summaries_detail, name='summaries_detail'),
]
