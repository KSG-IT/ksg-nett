from django.db.models import Q, Case, When, CharField
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
                    then=Concat("first_name", "last_name"),
                ),
                default="username",
                output_field=CharField(),
            )
        )
        result = annotated_qs.filter(
            Q(email__iregex=value) | Q(phone=value) | Q(full_name__iregex=value)
        ).distinct()
        return result
