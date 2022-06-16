from django.db import models


class Priority(models.TextChoices):
    FIRST = ("first", "First")
    SECOND = ("second", "Second")
    THIRD = ("third", "Third")


class AdmissionStatus(models.TextChoices):
    INITIALIZATION = ("configuration", "Configuration")
    OPEN = ("open", "Open")
    IN_SESSION = ("in-session", "In session")
    LOCKED = ("locked", "Locked")
    CLOSED = ("closed", "Closed")


class ApplicantStatus(models.TextChoices):
    EMAIL_SENT = ("email-sent", "Email sent")
    HAS_REGISTERED_PROFILE = ("has-registered-profile", "Has registered profile")
    HAS_SET_PRIORITIES = ("has-set-priorities", "Has set priorities")
    SCHEDULED_INTERVIEW = ("scheduled-interview", "Scheduled interview")
    INTERVIEW_FINISHED = ("interview-finished", "Interview finished")
    DID_NOT_SHOW_UP_FOR_INTERVIEW = (
        "did-not-show-up-for-interview",
        "Did not show up for interview",
    )
    TO_BE_CALLED = ("to-be-called", "To be called")
    ACCEPTED = ("accepted", "Accepted")
    REJECTED = ("rejected", "Rejected")
    RETRACTED_APPLICATION = ("retracted-application", "Retracted application")


class InternalGroupStatus(models.TextChoices):
    WANT = ("want", "Want")
    DO_NOT_WANT = ("do-not-want", "Do not want")
    RESERVE = ("reserve", "Reserve")
    CURRENTLY_DISCUSSING = ("currently-discussing", "Currently discussing")
    SHOULD_BE_ADMITTED = ("should-be-admitted", "Should be admitted")
    PASS_AROUND = ("pass-around", "Pass around")
