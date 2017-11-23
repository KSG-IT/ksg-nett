from django.conf.urls import url

from quotes import views

urlpatterns = [
    url('^', views.list_view),
]
