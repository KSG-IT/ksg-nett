from django.conf.urls import url

from users.views import CurrentUserView

urlpatterns = [
    url('current-user/', CurrentUserView.as_view())
]
