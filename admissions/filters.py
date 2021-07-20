from django_filters import FilterSet, OrderingFilter, CharFilter, NumberFilter
from admissions.models import Applicant, Admission
from graphene_django.filter import GlobalIDMultipleChoiceFilter
from django.db.models import Q, Sum, F, FloatField


class ApplicantFilter(FilterSet):
    class Meta:
        model = Applicant
        fields = ("first_name",)


class AdmissionFilter(FilterSet):
    class Meta:
        model = Admission
        fields = ("date",)
