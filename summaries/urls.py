from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.summaries_list),
    url(r'(?P<summary_id>[0-9]+)', views.summaries_detail),
]
