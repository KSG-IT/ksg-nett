import graphene
from graphene_django.types import DjangoObjectType
from .models import Event
from django.contrib.auth import get_user_model