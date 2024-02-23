from django.db.models import Q, Case, When, CharField, Value as V
from django_filters import FilterSet, CharFilter, OrderingFilter, BooleanFilter
from django.db.models.functions import Concat


class UserFilter(FilterSet):
    q = CharFilter(method="get_q")
    order_by = OrderingFilter(
        fields={
            "first_name": "firstName",
            "last_name": "lastName",
            "phone": "phone",
        }
    )

    is_active = BooleanFilter(field_name="is_active")

    def get_q(self, queryset, name, value):
        annotated_qs = queryset.annotate(
            full_name=Case(
                When(
                    ~Q(first_name="") & ~Q(last_name=""),
                    then=Concat("first_name", V(" "), "last_name"),
                ),
                default="username",
                output_field=CharField(),
            )
        )
        result = annotated_qs.filter(
            Q(email__iregex=value) | Q(phone=value) | Q(full_name__iregex=value)
        ).distinct()
        return result

class AdvancedUserFilter(FilterSet):
    q = CharFilter(method="get_advanced_q")
    order_by = OrderingFilter(
        fields={
            "first_name": "firstName",
            "last_name": "lastName",
        }
    )

def get_advanced_q(self, queryset, name, value):
    is_active = value.get('is_active', []) # aktiv, pang, nyopptatt, nypang, z person
    is_gang = value.get('is_gang', []) # Bar, Sprit, Arr, Øko, Edgar, DH bar, DH brygg, Styret, Lyche bar, Lyche kjøkken
    is_staff = value.get('is_staff', []) # Gjengis, Funksjonær
    balance = value.get('balance', []) # 100, 200, 300, 500

    annotated_qs = queryset.annotate(
        full_name=Case(
            When(
                ~Q(first_name="") & ~Q(last_name=""),
                then=Concat("first_name", Value(" "), "last_name"),
            ),
            default="username",
            output_field=CharField(),
        )
    )

    if is_active:
        active_query = Q()
        for value in is_active:
            active_query |= Q(is_active=value)
        annotated_qs = annotated_qs.filter(active_query)

    if is_gang:
        gang_query = Q()
        for value in is_gang:
            gang_query |= Q(internal_group_position_history__position__internal_group__name=value)
        annotated_qs = annotated_qs.filter(gang_query)
    
    if is_staff:
        staff_query = Q()
        for value in is_staff:
            staff_query |= Q(is_staff=value)
        annotated_qs = annotated_qs.filter(staff_query)

    if balance:
        balance_query = Q()
        for value in balance:
            balance_query |= Q(balance=value)
        annotated_qs = annotated_qs.filter(balance_query)

    result = annotated_qs.filter(
        Q(full_name__iregex=value)
    ).distinct()

    return result
