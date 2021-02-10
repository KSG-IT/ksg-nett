from django.urls import path

from organization import views

urlpatterns = [
    path(
        "internal-groups/<int:internal_group_id>",
        views.internal_groups_detail,
        name="internal_groups_detail",
    ),
    path(
        "internal-groups/<int:internal_group_id>/edit",
        views.internal_groups_edit,
        name="internal_groups_edit",
    ),
]
