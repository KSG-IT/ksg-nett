from django.urls import path

from organization import views

urlpatterns = [
    path("internal-groups/<int:internal_group_id>", views.internal_group),
]
