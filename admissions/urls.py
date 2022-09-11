from django.urls import path

from admissions import views

urlpatterns = [
    path("callsheet", views.download_callsheet_workbook, name="callsheet"),
]
