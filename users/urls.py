from django.urls import path

from . import views

urlpatterns = [
    path('current-user/', views.current_user, name='profile'), # replace with <int_user_id>
    path('current-user/edit/', views.edit_current_user), # replace with <int:user_id>/update?
    path('<int:user_id>', views.get_user, name='user_details'),
    path('<int:user_id>/update', views.update_user)
]
