from django.contrib import admin

from admissions.models import (
    Admission,
    Applicant,
    InternalGroupPositionPriority,
    Interview,
    InterviewAdditionalEvaluationStatement,
    InterviewAdditionalEvaluationAnswer,
    InterviewBooleanEvaluationAnswer,
    InterviewBooleanEvaluation,
    InterviewScheduleTemplate,
    InterviewLocation,
    InterviewLocationAvailability,
    ApplicantUnavailability,
    ApplicantInterest,
    AdmissionAvailableInternalGroupPositionData,
)


class AdmissionAvailableInternalGroupPositionDataInline(admin.TabularInline):
    model = AdmissionAvailableInternalGroupPositionData
    extra = 1


class InterviewAdditionalEvaluationAnswerInline(admin.TabularInline):
    model = InterviewAdditionalEvaluationAnswer
    extra = 1


class InterviewBooleanEvaluationAnswerInline(admin.TabularInline):
    model = InterviewBooleanEvaluationAnswer
    extra = 1


class InternalGroupPositionPriorityInline(admin.TabularInline):
    model = InternalGroupPositionPriority
    extra = 1


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    inlines = (
        InterviewAdditionalEvaluationAnswerInline,
        InterviewBooleanEvaluationAnswerInline,
    )


@admin.register(InterviewBooleanEvaluation)
class InterviewBooleanEvaluationAdmin(admin.ModelAdmin):
    pass


@admin.register(InterviewBooleanEvaluationAnswer)
class InterviewBooleanEvaluationAnswerAdmin(admin.ModelAdmin):
    pass


@admin.register(InterviewAdditionalEvaluationStatement)
class InterviewAdditionalEvaluationAdmin(admin.ModelAdmin):
    pass


@admin.register(InterviewAdditionalEvaluationAnswer)
class InterviewAdditionalEvaluationAnswerAdmin(admin.ModelAdmin):
    pass


@admin.register(InterviewScheduleTemplate)
class InterviewScheduleTemplateAdmin(admin.ModelAdmin):
    pass


@admin.register(ApplicantUnavailability)
class ApplicantUnavailabilityAdmin(admin.ModelAdmin):
    pass


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    inlines = (AdmissionAvailableInternalGroupPositionDataInline,)


@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    inlines = [InternalGroupPositionPriorityInline]


@admin.register(InternalGroupPositionPriority)
class InternalGroupPriorityAdmin(admin.ModelAdmin):
    pass


@admin.register(InterviewLocation)
class InterviewScheduleLocationTemplateAdmin(admin.ModelAdmin):
    pass


@admin.register(InterviewLocationAvailability)
class InterviewScheduleLocationAvailabilityAdmin(admin.ModelAdmin):
    pass


@admin.register(ApplicantInterest)
class ApplicantInterestAdmin(admin.ModelAdmin):
    pass
