from django.db.models import Q, Case, When, CharField
from django.db.models.functions import Concat
from django_filters import FilterSet, CharFilter


class QuoteFilter(FilterSet):
    q = CharFilter(method="get_q")

    def get_q(self, queryset, name, value):
        """
        In the future expand this to allow the `q` variable to search after names of participants
            - Annotated full_name from first_name and last_name through tagged users
        """

        # Allows users to search for both context and content text
        result = queryset.filter(Q(text__icontains=value) | Q(context__icontains=value))
        return result
