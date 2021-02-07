from django.db import models
from common.util import get_semester_year_shorthand

class Applicant(models.Model):
    name = models.CharField(default="", null=False, max_length=100)
    phone = models.CharField(default="", blank=True, max_length=50)
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField(blank=True, null=True)
    study = models.CharField(default="", blank=True, max_length=100)


class Admissions(models.Model):
    applicants = models.ForeignKey(Applicant)
    date = models.DateField(blank=True, null=True)
    admission_closed = models.BooleanField(default=False)

    def get_admissions_by_semester(self) -> str:
        return get_semester_year_shorthand(self.date)
    



    

