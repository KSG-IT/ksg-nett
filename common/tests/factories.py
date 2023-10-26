from common.models import FeatureFlag

import pytz
from django.utils import timezone
from factory import SubFactory, Faker, Sequence, post_generation
from factory.django import DjangoModelFactory
from factory.django import ImageField


class FeatureFlagFactory(DjangoModelFactory):
    class Meta:
        model = FeatureFlag
