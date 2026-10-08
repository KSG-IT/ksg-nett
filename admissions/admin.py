from django.contrib import admin
from django.db.models import Count

from admissions.models import (
    Admission,
    Applicant,
    ApplicantComment,
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
    ApplicantRecommendation,
)

APPLICANT_SEARCH_FIELDS = [
    "applicant__first_name",
    "applicant__last_name",
    "applicant__email",
]


class AdmissionAvailableInternalGroupPositionDataInline(admin.TabularInline):
    model = AdmissionAvailableInternalGroupPositionData
    extra = 1
    autocomplete_fields = ["internal_group_position"]


class InterviewAdditionalEvaluationAnswerInline(admin.TabularInline):
    model = InterviewAdditionalEvaluationAnswer
    extra = 1


class InterviewBooleanEvaluationAnswerInline(admin.TabularInline):
    model = InterviewBooleanEvaluationAnswer
    extra = 1


class InternalGroupPositionPriorityInline(admin.TabularInline):
    model = InternalGroupPositionPriority
    extra = 1
    autocomplete_fields = ["internal_group_position"]


class ApplicantInline(admin.StackedInline):
    model = Applicant
    fields = ["admission", "first_name", "last_name", "email", "phone", "study"]
    can_delete = False


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "interview_start",
        "interview_end",
        "location",
        "applicant",
        "total_evaluation",
        "registered_at_samfundet",
    ]
    list_filter = [
        "location",
        "total_evaluation",
        "registered_at_samfundet",
        "interview_start",
    ]
    search_fields = [
        "applicant__first_name",
        "applicant__last_name",
        "applicant__email",
        "location__name",
    ]
    date_hierarchy = "interview_start"
    autocomplete_fields = ["interviewers"]
    inlines = (
        InterviewAdditionalEvaluationAnswerInline,
        InterviewBooleanEvaluationAnswerInline,
        ApplicantInline,
    )

    def get_queryset(self, request):
        # __str__ renders the location, also in autocomplete results. A
        # select_related() here makes the changelist ignore list_select_related.
        return super().get_queryset(request).select_related("location", "applicant")


@admin.register(InterviewBooleanEvaluation)
class InterviewBooleanEvaluationAdmin(admin.ModelAdmin):
    list_display = ["statement", "order"]


@admin.register(InterviewBooleanEvaluationAnswer)
class InterviewBooleanEvaluationAnswerAdmin(admin.ModelAdmin):
    list_display = ["id", "interview", "statement", "value"]
    list_select_related = ["interview__location", "statement"]
    list_filter = ["statement", "value"]
    autocomplete_fields = ["interview"]


@admin.register(InterviewAdditionalEvaluationStatement)
class InterviewAdditionalEvaluationAdmin(admin.ModelAdmin):
    list_display = ["statement", "order"]


@admin.register(InterviewAdditionalEvaluationAnswer)
class InterviewAdditionalEvaluationAnswerAdmin(admin.ModelAdmin):
    list_display = ["id", "interview", "statement", "answer"]
    list_select_related = ["interview__location", "statement"]
    list_filter = ["statement", "answer"]
    autocomplete_fields = ["interview"]


@admin.register(InterviewScheduleTemplate)
class InterviewScheduleTemplateAdmin(admin.ModelAdmin):
    pass


@admin.register(ApplicantUnavailability)
class ApplicantUnavailabilityAdmin(admin.ModelAdmin):
    list_display = ["id", "applicant", "datetime_start", "datetime_end"]
    list_select_related = ["applicant"]
    search_fields = APPLICANT_SEARCH_FIELDS
    autocomplete_fields = ["applicant"]


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ["__str__", "date", "status", "applicant_count", "closed_at"]
    list_filter = ["status"]
    inlines = (AdmissionAvailableInternalGroupPositionDataInline,)

    def get_queryset(self, request):
        return (
            super().get_queryset(request).annotate(applicant_count=Count("applicants"))
        )

    @admin.display(description="Applicants", ordering="applicant_count")
    def applicant_count(self, admission):
        return admission.applicant_count


@admin.register(Applicant)
class ApplicantAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "email",
        "phone",
        "admission",
        "status",
        "will_be_admitted",
    ]
    list_select_related = ["admission"]
    list_filter = [
        "admission",
        "status",
        "will_be_admitted",
        "wants_digital_interview",
        "open_for_other_positions",
    ]
    inlines = [InternalGroupPositionPriorityInline]
    search_fields = ["first_name", "last_name", "email", "phone"]
    autocomplete_fields = ["interview", "notice_user"]


@admin.register(InternalGroupPositionPriority)
class InternalGroupPriorityAdmin(admin.ModelAdmin):
    # InternalGroupPositionPriority.__str__ loads the applicant, admission and position
    list_display = [
        "id",
        "applicant",
        "internal_group_position",
        "applicant_priority",
        "internal_group_priority",
    ]
    # The action checkbox label renders __str__, which needs the admission
    list_select_related = [
        "applicant__admission",
        "internal_group_position__internal_group",
    ]
    list_filter = [
        "applicant__admission",
        "applicant_priority",
        "internal_group_priority",
        "internal_group_position__internal_group",
    ]
    search_fields = APPLICANT_SEARCH_FIELDS
    autocomplete_fields = ["applicant", "internal_group_position"]


@admin.register(InterviewLocation)
class InterviewScheduleLocationTemplateAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(InterviewLocationAvailability)
class InterviewScheduleLocationAvailabilityAdmin(admin.ModelAdmin):
    list_display = ["id", "interview_location", "datetime_from", "datetime_to"]
    list_select_related = ["interview_location"]
    list_filter = ["interview_location"]


@admin.register(ApplicantInterest)
class ApplicantInterestAdmin(admin.ModelAdmin):
    list_display = ["id", "applicant", "internal_group", "position_to_be_offered"]
    list_select_related = [
        "applicant",
        "internal_group",
        "position_to_be_offered__internal_group",
    ]
    list_filter = ["applicant__admission", "internal_group"]
    search_fields = APPLICANT_SEARCH_FIELDS
    autocomplete_fields = ["applicant", "position_to_be_offered"]


@admin.register(AdmissionAvailableInternalGroupPositionData)
class AdmissionAvailableInternalGroupPositionDataAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "admission",
        "internal_group_position",
        "membership_type",
        "available_positions",
    ]
    list_select_related = ["admission", "internal_group_position__internal_group"]
    list_filter = ["admission", "membership_type"]
    autocomplete_fields = ["internal_group_position"]


@admin.register(ApplicantComment)
class ApplicantCommentAdmin(admin.ModelAdmin):
    list_display = ["id", "applicant", "user", "created_at"]
    list_select_related = ["applicant", "user"]
    list_filter = ["applicant__admission"]
    search_fields = APPLICANT_SEARCH_FIELDS + ["text"]
    autocomplete_fields = ["applicant", "user"]


@admin.register(ApplicantRecommendation)
class ApplicantRecommendationAdmin(admin.ModelAdmin):
    list_display = ["id", "applicant", "internal_group", "recommended_by", "created_at"]
    list_select_related = ["applicant", "internal_group", "recommended_by"]
    list_filter = ["applicant__admission", "internal_group"]
    search_fields = APPLICANT_SEARCH_FIELDS + ["reasoning"]
    autocomplete_fields = ["applicant", "recommended_by"]
