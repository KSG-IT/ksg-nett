from django.conf.urls import url

from users.views import current_user

urlpatterns = [
    url('current-user/', current_user)
]
