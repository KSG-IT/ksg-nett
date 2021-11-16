from django.db import models
from common.util import get_semester_year_shorthand
from admissions.consts import (
    Priority,
    ApplicantStatus,
    InternalGroupStatus,
    AdmissionStatus,
)


class Admission(models.Model):
    date = models.DateField(blank=True, null=True)
    status = models.CharField(
        choices=AdmissionStatus.choices, default=AdmissionStatus.OPEN, max_length=12
    )

    @property
    def semester(self) -> str:
        return get_semester_year_shorthand(self.date)

    @property
    def number_of_applicants(self):
        return self.applicants.count()

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

    image = models.ImageField(upload_to="applicants", null=True)

    # Tracks whether or not the applicant has retracted their application
    status = models.CharField(
        choices=ApplicantStatus.choices, max_length=12, default=ApplicantStatus.ACTIVE
    )

    @property
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"Applicant {self.get_full_name}"


class InternalGroupPriority(models.Model):
    class Meta:
        verbose_name = "Internal group priority"
        verbose_name_plural = "Internal group priorities"
        unique_together = ("applicant", "applicant_priority")

    applicant = models.ForeignKey(
        Applicant, on_delete=models.CASCADE, related_name="priorities"
    )
    internal_group = models.ForeignKey(
        "organization.InternalGroup",
        on_delete=models.CASCADE,
        related_name="application_priorities",
    )

    # Tells us how the applicant prioritizes internal groups in their application
    applicant_priority = models.CharField(choices=Priority.choices, max_length=12)

    # Tells us how an internal group prioritizes an applicant, null means not considered yet
    internal_group_priority = models.CharField(
        choices=InternalGroupStatus.choices,
        max_length=24,
        blank=True,
        null=True,
        default="",
    )

    def __str__(self):
        return (
            f"Admission {self.applicant.admission.semester} "
            f"{self.internal_group.name} {self.applicant_priority} choice for {self.applicant.get_full_name}"
        )
