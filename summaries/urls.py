from django.urls import path, re_path

from . import views

urlpatterns = [
    re_path(r'^$', views.summaries_list, name='summaries_list'),
    path('create', views.summaries_create, name='summaries_create'),
    path('search', views.summaries_search, name='summaries_search'),
    path('last', views.summaries_last, name='summaries_last'),
    path('archive', views.summaries_archive, name='summaries_archive'),
    path('<int:summary_id>/update', views.summaries_update, name='summaries_update'),
    path('<int:summary_id>/delete', views.summaries_delete, name='summaries_delete'),
    path('<int:summary_id>', views.summaries_detail, name='summaries_detail'),
]
