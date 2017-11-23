from django.conf.urls import url

from quotes import views

urlpatterns = [
    url('(?P<quote_id>[0-9])/vote-up', views.vote_up),
    url('^', views.list_view),
]
