from admissions.consts import ApplicantStatus

APPLICANT_FACTORY_STATUS_CHOICES = [
    ApplicantStatus.EMAIL_SENT,
    ApplicantStatus.HAS_REGISTERED_PROFILE,
    ApplicantStatus.SCHEDULED_INTERVIEW,
    ApplicantStatus.INTERVIEW_FINISHED,
    ApplicantStatus.DID_NOT_SHOW_UP_FOR_INTERVIEW,
    ApplicantStatus.RETRACTED_APPLICATION,
]
