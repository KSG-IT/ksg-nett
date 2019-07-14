from django.db import models
from django.db.models import Sum
from django.utils import timezone


class QuoteDefaultQuerySet(models.QuerySet):
    """
    This class returns quotes as a function of the semester they were submitted.
    """
    def pending(self):
        return self.filter(
            verified_by__isnull=True
        )

    def verified(self):
        return self.filter(
            verified_by__isnull=False
        )

    def this_semester(self):
        """
        Returns all quotes where the creation date spans within the current semester
        """
        current_time = timezone.now()
        start_of_semester = current_time
        if current_time.month > 7:
            start_of_semester = timezone.datetime(
                current_time.year, 7, 1, tzinfo=current_time.tzinfo
            )
        else:
            start_of_semester = timezone.datetime(
                current_time.year, 1, 1, tzinfo=current_time.tzinfo
            )

            return self.filter(created_at__gte=start_of_semester)

    def previous_semesters(self):
        """
        Returns all quotes that were created before the current semester
        """
        current_time = timezone.now()
        if current_time.month > 7:
            start_of_semester = timezone.datetime(
                current_time.year, 7, 1, tzinfo=current_time.tzinfo
            )
        else:
            start_of_semester = timezone.datetime(
                current_time.year, 1, 1, tzinfo=current_time.tzinfo
            )

        return self.filter(created_at__lt=start_of_semester)

    def in_semester(self, some_datetime_in_semester: timezone.datetime):
        # Case where we are in the autumn
        if some_datetime_in_semester.month > 7:
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
            created_at__gte=start_of_semester, created_at__lt=end_of_semester
        )

    def semester_highest_score(self, some_semester: timezone.datetime):
        semester_queryset = self.in_semester(some_datetime_in_semester=some_semester)
        return semester_queryset.annotate(total_votes=Sum('votes')).order_by('-total_votes')
