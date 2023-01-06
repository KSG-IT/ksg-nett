from django.urls import path
from . import views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path("print-list", csrf_exempt(views.download_soci_session_list_pdf)),
]
