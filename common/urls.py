from django.conf.urls import url
from django.urls import path

from common import views

urlpatterns = [
    url(r'^$', views.index),
    path("test-pdf-print", views.print_pdf_example)
]
