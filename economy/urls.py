from django.urls import path
from . import views
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [path("stripe-webhook", csrf_exempt(views.stripe_webhook))]
