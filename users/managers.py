from django.contrib.auth.models import UserManager
from django.utils import timezone


class UsersHaveMadeOutManager(UserManager):
    def this_semester(self) -> timezone.datetime:
        """
        Returns all made out objects that have been registered later than the start of
        'this semester'.
        :return:
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

        return self.get_queryset().filter(created__gte=start_of_semester)

    def in_semester(self, some_datetime_in_semester: timezone.datetime):
        """
        Returns all made out objects that was registered after or equal to the start of the semester,
        before the start of the next semester. "The semester" is defined by the input date, as
        every date is necessarily part of some semester.

        :param some_datetime_in_semester:
        :return:
        """
        start_of_semester = some_datetime_in_semester
        end_of_semester = some_datetime_in_semester

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

        return self.get_queryset().filter(
            created__gte=start_of_semester, created__lt=end_of_semester
        )
