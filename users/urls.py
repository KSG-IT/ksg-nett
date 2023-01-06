from django.urls import path

from users import views

urlpatterns = [
    path("<int:user_id>", views.user_detail, name="user_detail"),
    path("klinekart", views.klinekart, name="klinekart"),
]
