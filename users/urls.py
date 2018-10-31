from django.urls import path

from users.views import current_user, edit_current_user

urlpatterns = [
    path('current-user/', current_user, name='profile'),
    path('current-user/edit/', edit_current_user)
]
