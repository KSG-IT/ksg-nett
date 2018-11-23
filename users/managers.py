from django.contrib.auth.models import UserManager
from django.db import models
from django.utils import timezone


class UsersHaveMadeOutManager(UserManager):
    def this_semester(self) -> timezone.datetime:
        current_time = timezone.now()
        start_of_semester = current_time
        if current_time.month > 7:
            start_of_semester = timezone.datetime(current_time.year, 7, 1, tzinfo=current_time.tzinfo)
        else:
            start_of_semester = timezone.datetime(current_time.year, 1, 1, tzinfo=current_time.tzinfo)

        return self.get_queryset().filter(created_at__gte=start_of_semester)

    def in_semester(self, some_datetime_in_semester: timezone.datetime):
        start_of_semester = some_datetime_in_semester
        end_of_semester = some_datetime_in_semester

        if some_datetime_in_semester.month > 7:
            start_of_semester = timezone.datetime(
                some_datetime_in_semester.year, 7, 1, tzinfo=some_datetime_in_semester.tzinfo)
            end_of_semester = timezone.datetime(
                some_datetime_in_semester.year + 1, 1, tzinfo=some_datetime_in_semester.tzinfo)
        else:
            start_of_semester = timezone.datetime(
                some_datetime_in_semester.year, 1, 1, tzinfo=some_datetime_in_semester.tzinfo)
            end_of_semester = timezone.datetime(
                some_datetime_in_semester.year, 7, 30, tzinfo=some_datetime_in_semester.tzinfo)

        return self.get_queryset().filter(created_at__gte=start_of_semester, created_at__lte=start_of_semester)
