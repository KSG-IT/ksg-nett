from django.db import models
from common.util import get_semester_year_shorthand


class Admission(models.Model):
    date = models.DateField(blank=True, null=True)
    admission_closed = models.BooleanField(default=False)

    @property
    def semester(self) -> str:
        return get_semester_year_shorthand(self.date)

    def __str__(self):
        return f"Admission for {self.semester}"


class Applicant(models.Model):
    admission = models.ForeignKey(
        Admission, on_delete=models.CASCADE, related_name="applicants"
    )
    first_name = models.CharField(null=False, max_length=100)
    last_name = models.CharField(null=False, max_length=100)

    phone = models.CharField(default="", null=True, blank=True, max_length=12)
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(blank=True)

    study = models.CharField(default="", blank=True, max_length=18)
    home_address = models.CharField(default="", blank=True, max_length=30)
    town_address = models.CharField(default="", blank=True, max_length=30)

    @property
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"Applicant {self.get_full_name}"
