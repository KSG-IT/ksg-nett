from django.urls import path
from . import views

urlpatterns = [
    path('', views.economy_home, name='economy_home'),
    path('deposit/', views.deposits, name='economy_deposit'),
    path('deposit/<int:deposit_id>', views.deposit_detail, name='economy_deposit_detail'),
    path('deposit/<int:deposit_id>/approve', views.deposit_approve, name='economy_approve_deposit'),
    path('deposit/<int:deposit_id>/invalidate', views.deposit_invalidate, name='economy_invalidate_deposit'),
    path('deposit/<int:deposit_id>/edit', views.deposit_edit, name='economy_edit_deposit'),
    path("soci-sessions", views.soci_sessions, name="economy_soci_sessions"),
    path("soci-sessions-closed", views.soci_sessions_closed, name="economy_soci_sessions_closed"),
    path("soci-sessions-open", views.soci_sessions_open, name="economy_soci_sessions_open"),
    path("soci-sessions/create", views.soci_session_create, name="economy_soci_session_create"),
    path("soci-sessions/<int:soci_session_id>/delete", views.soci_session_delete, name="economy_soci_session_delete"),
    path("soci-sessions/<int:soci_session_id>/close", views.soci_session_close, name="economy_soci_session_close"),
    path("soci-sessions/<int:soci_session_id>", views.soci_session_detail, name="economy_soci_session_detail"),
    path("soci-sessions/<int:soci_session_id>/product-order/add", views.product_order_add),
    path("product-orders/<int:product_order_id>/delete", views.product_order_delete,
         name="economy_product_orders_delete"),
]
