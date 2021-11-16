from django.db import models


class Priority(models.TextChoices):
    FIRST = ("first", "First")
    SECOND = ("second", "Second")
    THIRD = ("third", "Third")


class ApplicantStatus(models.TextChoices):
    ACTIVE = ("active", "Active")
    RETRACTED = ("retracted", "Retracted")


class InternalGroupStatus(models.TextChoices):
    WANT = (
        "want",
        "Want",
    )
    DO_NOT_WANT = (
        "do-not-want",
        "Do not want",
    )
    RESERVE = ("reserve", "Reserve")
    SHOULD_BE_ADMITTED = ("should-be-admitted", "Should be admitted")
