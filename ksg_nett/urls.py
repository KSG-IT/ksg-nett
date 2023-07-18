"""ksg_nett URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path

from graphene_file_upload.django import FileUploadGraphQLView
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import RedirectView


def trigger_error(request):
    division_by_zero = 1 / 0


def health_check(request):
    return HttpResponse(
        "OK",
    )


urlpatterns = [
    # Website
    path("", include("common.urls")),
    path("health-check", health_check),
    path("external/", include("external.urls")),
    path("users/", include("users.urls")),
    path("economy/", include("economy.urls")),
    path("schedules/", include("schedules.urls")),
    path("admissions/", include("admissions.urls")),
    # Developer
    path("admin/", admin.site.urls),
    path(
        "graphql/",
        csrf_exempt(FileUploadGraphQLView.as_view(graphiql=settings.GRAPHIQL)),
    ),
    path("sentry-debug/", trigger_error),
    path("", RedirectView.as_view(url="admin")),
    path(
        "api/",
        include(
            (
                [
                    path("", include("api.urls")),
                ],
                "api",
            ),
            namespace="api",
        ),
    ),
]

# Should only be done in dev
# https://stackoverflow.com/questions/23740169/apache-django-and-static-and-media-file-serving
urlpatterns += static("/media", document_root=settings.MEDIA_ROOT)

# TODO: When we are ready to move to production, we should consider moving media serving
# to a service such as AWS s3
