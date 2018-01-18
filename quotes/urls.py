from django.conf.urls import url

from quotes import views

urlpatterns = [
    url('(?P<quote_id>[0-9]+)/vote-up', views.vote_up),
    url('(?P<quote_id>[0-9]+)/vote-down', views.vote_down),
    url('^add', views.quotes_add),
    url('^', views.quotes_list),
]
