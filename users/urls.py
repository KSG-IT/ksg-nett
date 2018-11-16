from django.urls import path

from users import views

urlpatterns = [
    path('<int:user_id>', views.user_detail, name='user_detail'),
    path('<int:user_id>/update', views.update_user, name='update_user')
]
