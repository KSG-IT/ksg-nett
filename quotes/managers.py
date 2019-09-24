from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.db.models.functions import Coalesce


class QuoteDefaultQuerySet(models.QuerySet):
    """
    This class returns quotes as a function of the semester they were submitted.
    """
    def in_semester(self, some_datetime_in_semester: timezone.datetime):
        # Case where we are in the autumn
        if some_datetime_in_semester.month >= 7:
            start_of_semester = timezone.datetime(
                some_datetime_in_semester.year,
                7,  # July
                1,  # First of
                tzinfo=some_datetime_in_semester.tzinfo,
            )
            end_of_semester = timezone.datetime(
                some_datetime_in_semester.year + 1,  # Next year
                1,  # January
                1,  # First of
                tzinfo=some_datetime_in_semester.tzinfo,
                )
        # Case where we are in the spring
        else:
            start_of_semester = timezone.datetime(
                some_datetime_in_semester.year,
                1,  # January
                1,  # First of
                tzinfo=some_datetime_in_semester.tzinfo,
            )
            end_of_semester = timezone.datetime(
                some_datetime_in_semester.year,
                7,  # July
                1,  # First of
                tzinfo=some_datetime_in_semester.tzinfo,
            )

        return self.filter(
            created__gte=start_of_semester, created__lt=end_of_semester
        )

    def semester_highest_score(self, some_semester: timezone.datetime):
        semester_queryset = self.in_semester(some_datetime_in_semester=some_semester)
        semester_queryset = semester_queryset.filter(verified_by__isnull=False)
        return semester_queryset.annotate(total_votes=Coalesce(Sum('votes__value'), 0)).order_by('-total_votes')[:10]

    def highest_score_all_time(self):
        return self.all().annotate(total_votes=Coalesce(Sum('votes__value'), 0)).order_by('-total_votes')[:10]




