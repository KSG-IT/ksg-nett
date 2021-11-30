from django.db.models import Q
from django_filters import FilterSet, CharFilter


class SummaryFilter(FilterSet):
    q = CharFilter(method="get_q")

    def get_q(self, queryset, name, value):
        """
        In the future expand this to allow the `q` variable to search after names of participants
            - Annotated full_name from first_name and last_name through participants
        """

        result = queryset.filter(Q(contents__icontains=value)).distinct()
        return result.order_by("date")
