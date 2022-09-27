from django.urls import path
from common import views

urlpatterns = [path("", views.index), path("test-pdf-print", views.print_pdf_example)]
