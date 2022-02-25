import datetime
import graphene
from graphene import Node
from graphene_django import DjangoObjectType
from django.db import IntegrityError
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from common.util import date_time_combiner
from django.db.models import Q
from graphene_django.filter import DjangoFilterConnectionField
from admissions.utils import (
    generate_interviews_from_schedule,
    resend_auth_token_email,
    obfuscate_admission,
)
from django.core.exceptions import SuspiciousOperation
from django.utils import timezone
from admissions.models import (
    Applicant,
    Admission,
    AdmissionAvailableInternalGroupPositionData,
    InternalGroupPositionPriority,
    Interview,
    InterviewLocation,
    InterviewLocationAvailability,
    InterviewScheduleTemplate,
    InterviewBooleanEvaluation,
    InterviewAdditionalEvaluationStatement,
)
from organization.models import InternalGroupPosition
from organization.schema import InternalGroupPositionNode
from admissions.filters import AdmissionFilter, ApplicantFilter
from admissions.consts import AdmissionStatus
from graphene_django_cud.types import TimeDelta
from graphene import Time, Date


class InternalGroupPositionPriorityNode(DjangoObjectType):
    class Meta:
        model = InternalGroupPositionPriority
        interfaces = (Node,)


class InterviewLocationAvailabilityNode(DjangoObjectType):
    class Meta:
        model = InterviewLocationAvailability
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return InterviewLocationAvailability.objects.get(pk=id)


class InterviewLocationNode(DjangoObjectType):
    class Meta:
        model = InterviewLocation
        interfaces = (Node,)

    availability = graphene.List(InterviewLocationAvailabilityNode)

    def resolve_availability(self: InterviewLocation, info, *args, **kwargs):
        return self.availability.all().order_by("datetime_from")

    @classmethod
    def get_node(cls, info, id):
        return InterviewLocation.objects.get(pk=id)


class ApplicantNode(DjangoObjectType):
    class Meta:
        model = Applicant
        interfaces = (Node,)

    full_name = graphene.String(source="get_full_name")

    @classmethod
    def get_node(cls, info, id):
        return Applicant.objects.get(pk=id)


class InterviewScheduleTemplateNode(DjangoObjectType):
    class Meta:
        model = InterviewScheduleTemplate
        interfaces = (Node,)

    default_interview_duration = TimeDelta()
    default_pause_duration = TimeDelta()

    interview_period_start_date = Date()
    interview_period_end_date = Date()

    default_interview_day_start = Time()
    default_interview_day_end = Time()

    def resolve_interview_period_start_date(
        self: InterviewScheduleTemplate, info, *args, **kwargs
    ):
        return self.interview_period_start_date

    def resolve_interview_period_end_date(
        self: InterviewScheduleTemplate, info, *args, **kwargs
    ):
        return self.interview_period_end_date

    def resolve_default_interview_day_start(
        self: InterviewScheduleTemplate, info, *args, **kwargs
    ):
        return self.default_interview_day_start

    def resolve_default_interview_day_end(
        self: InterviewScheduleTemplate, info, *args, **kwargs
    ):
        return self.default_interview_day_end

    def resolve_default_interview_duration(
        self: InterviewScheduleTemplate, info, *args, **kwargs
    ):
        # This is a timedelta object but is returned as "mm:ss" instead of "hh:mm:ss" which ruins stuff kinda
        return self.default_interview_duration

    def resolve_default_pause_duration(
        self: InterviewScheduleTemplate, info, *args, **kwargs
    ):
        return self.default_pause_duration

    @classmethod
    def get_node(cls, info, id):
        return InterviewScheduleTemplate.objects.get(pk=id)


class AdmissionAvailableInternalGroupPositionDataNode(DjangoObjectType):
    class Meta:
        model = AdmissionAvailableInternalGroupPositionData
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return AdmissionAvailableInternalGroupPositionData.objects.get(pk=id)


class AdmissionNode(DjangoObjectType):
    class Meta:
        model = Admission
        interfaces = (Node,)

    semester = graphene.String(source="semester")
    available_internal_group_positions_data = graphene.NonNull(
        graphene.List(AdmissionAvailableInternalGroupPositionDataNode)
    )
    applicants = graphene.List(ApplicantNode)

    def resolve_applicants(self: Admission, info, *args, **kwargs):
        return self.applicants.all().order_by("first_name")

    def resolve_available_internal_group_positions_data(
        self: Admission, info, *args, **kwargs
    ):
        available_positions = self.available_internal_group_positions_data.all()
        if available_positions:
            return available_positions

        default_externally_available_positions = InternalGroupPosition.objects.filter(
            available_externally=True
        )
        for position in default_externally_available_positions:
            AdmissionAvailableInternalGroupPositionData.objects.create(
                internal_group_position=position, admission=self, available_positions=1
            )

        return self.available_internal_group_positions_data.all()

    @classmethod
    def get_node(cls, info, id):
        return Admission.objects.get(pk=id)


class InterviewNode(DjangoObjectType):
    class Meta:
        model = Interview
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return Interview.objects.get(pk=id)


class ApplicantQuery(graphene.ObjectType):
    applicant = Node.Field(ApplicantNode)
    all_applicants = DjangoFilterConnectionField(
        ApplicantNode, filterset_class=ApplicantFilter
    )
    get_applicant_from_token = graphene.Field(ApplicantNode, token=graphene.String())

    def resolve_get_applicant_from_token(self, info, token, *args, **kwargs):
        applicant = Applicant.objects.filter(token=token).first()
        return applicant

    def resolve_all_applicants(self, info, *args, **kwargs):
        return Applicant.objects.all().order_by("first_name")


class ResendApplicantTokenMutation(graphene.Mutation):
    class Arguments:
        email = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, email, *args, **kwargs):
        applicant = Applicant.objects.filter(email=email).first()
        if applicant:
            ok = resend_auth_token_email(applicant)
            return ResendApplicantTokenMutation(ok=ok)
        return ResendApplicantTokenMutation(ok=False)


class ApplicationData(graphene.ObjectType):
    email = graphene.String()


class CreateApplicationsMutation(graphene.Mutation):
    class Arguments:
        emails = graphene.List(graphene.String)

    ok = graphene.Boolean()
    applications_created = graphene.Int()
    faulty_emails = graphene.List(graphene.String)

    def mutate(self, info, emails):
        faulty_emails = []
        for email in emails:
            try:
                Applicant.create_or_update_application(email)
            except IntegrityError:
                faulty_emails.append(email)

        return CreateApplicationsMutation(
            ok=True,
            applications_created=len(emails) - len(faulty_emails),
            faulty_emails=faulty_emails,
        )


class AdmissionQuery(graphene.ObjectType):
    admission = Node.Field(AdmissionNode)
    all_admissions = DjangoFilterConnectionField(
        AdmissionNode, filterset_class=AdmissionFilter
    )
    active_admission = graphene.Field(AdmissionNode)
    all_interview_schedule_templates = graphene.List(InterviewScheduleTemplateNode)
    interview_schedule_template = graphene.Field(InterviewScheduleTemplateNode)
    externally_available_internal_group_positions = graphene.List(
        InternalGroupPositionNode
    )
    currently_admission_internal_group_position_data = graphene.List(
        AdmissionAvailableInternalGroupPositionDataNode
    )

    def resolve_currently_admission_internal_group_position_data(
        self, info, *args, **kwargs
    ):
        admission = Admission.get_active_admission()
        return admission.available_internal_group_positions_data.all()

    def resolve_interview_schedule_template(self, info, *args, **kwargs):
        return InterviewScheduleTemplate.get_interview_schedule_template()

    def resolve_all_interview_schedule_templates(self, info, *args, **kwargs):
        return InterviewScheduleTemplate.objects.all()

    def resolve_active_admission(self, info, *args, **kwargs):
        admission = Admission.objects.filter(~Q(status="closed"))
        if len(admission) > 1:
            raise Admission.MultipleObjectsReturned

        if not admission:
            return None

        return admission.first()

    def resolve_all_admissions(self, info, *args, **kwargs):
        return Admission.objects.all().order_by("-date")

    def resolve_externally_available_internal_group_positions(
        self, info, *args, **kwargs
    ):
        return InternalGroupPosition.objects.filter(available_externally=True).order_by(
            "name"
        )


class InterviewLocationDateGrouping(graphene.ObjectType):
    name = graphene.String()
    interviews = graphene.List(InterviewNode)


class InterviewDay(graphene.ObjectType):
    date = graphene.Date()
    locations = graphene.List(InterviewLocationDateGrouping)


class InterviewOverviewQuery(graphene.ObjectType):
    # We use this to orderly structure the interview overview for each day in the interview period
    interview_day_groupings = graphene.List(InterviewDay)
    interview_schedule_template = graphene.Field(InterviewScheduleTemplateNode)
    interview_count = graphene.Int()
    admission_id = graphene.ID()


class InterviewBooleanEvaluationStatementNode(DjangoObjectType):
    class Meta:
        model = InterviewBooleanEvaluation
        interfaces = (Node,)


class InterviewAdditionalEvaluationStatementNode(DjangoObjectType):
    class Meta:
        model = InterviewAdditionalEvaluationStatement
        interfaces = (Node,)


class InterviewTemplate(graphene.ObjectType):
    interview_boolean_evaluation_statements = graphene.List(
        InterviewBooleanEvaluationStatementNode
    )
    interview_additional_evaluation_statements = graphene.List(
        InterviewAdditionalEvaluationStatementNode
    )


class InterviewQuery(graphene.ObjectType):
    interview = Node.Field(InterviewNode)
    interview_template = graphene.Field(InterviewTemplate)

    def resolve_interview_template(self, info, *args, **kwargs):
        all_boolean_evaluation_statements = (
            InterviewBooleanEvaluation.objects.all().order_by("order")
        )
        all_additional_evaluation_statements = (
            InterviewAdditionalEvaluationStatement.objects.all().order_by("order")
        )
        return InterviewTemplate(
            interview_boolean_evaluation_statements=all_boolean_evaluation_statements,
            interview_additional_evaluation_statements=all_additional_evaluation_statements,
        )


class InterviewLocationQuery(graphene.ObjectType):
    all_interview_locations = graphene.List(InterviewLocationNode)
    interview_overview = graphene.Field(InterviewOverviewQuery)

    def resolve_interview_overview(self, info, *args, **kwargs):
        # We want to return all interviews in an orderly manner grouped by date and locations.
        interview_days = []
        schedule = InterviewScheduleTemplate.get_interview_schedule_template()
        date_cursor = schedule.interview_period_start_date
        interview_period_end = schedule.interview_period_end_date
        next_day = timezone.timedelta(days=1)
        start_of_day = datetime.time(hour=0, minute=0, second=0)
        while date_cursor <= interview_period_end:
            interview_locations = []
            # First we retrieve all interviews in a 24 hour time period
            datetime_cursor = date_time_combiner(date_cursor, start_of_day)
            interviews = Interview.objects.filter(
                interview_start__gt=datetime_cursor,
                interview_end__lt=datetime_cursor + next_day,
            )
            # Then we want to group them by interview location
            for location in InterviewLocation.objects.all().order_by("name"):
                location_filtered_interviews = interviews.filter(
                    location=location
                ).order_by("interview_start")

                # We only care about adding an entry if there are interviews in the given location
                if location_filtered_interviews:
                    interview_location_date_grouping = InterviewLocationDateGrouping(
                        name=location.name, interviews=location_filtered_interviews
                    )
                    interview_locations.append(interview_location_date_grouping)

            # We have found all interviews for this day, now we add it to the main query list
            # if it isn't empty
            if interview_locations:
                interview_days.append(
                    InterviewDay(date=date_cursor, locations=interview_locations)
                )
            date_cursor += next_day

        total_interviews = Interview.objects.all().count()
        return InterviewOverviewQuery(
            interview_day_groupings=interview_days,
            interview_schedule_template=schedule,
            interview_count=total_interviews,
            admission_id=Admission.get_active_admission().id,
        )

    def resolve_all_interview_locations(self, info, *args, **kwargs):
        return InterviewLocation.objects.all().order_by("name")


# === Applicant ===
class CreateApplicantMutation(DjangoCreateMutation):
    class Meta:
        model = Applicant


class PatchApplicantMutation(DjangoPatchMutation):
    class Meta:
        model = Applicant


class DeleteApplicantMutation(DjangoDeleteMutation):
    class Meta:
        model = Applicant


# === Admission ===
class CreateAdmissionMutation(DjangoCreateMutation):
    class Meta:
        model = Admission


class PatchAdmissionMutation(DjangoPatchMutation):
    class Meta:
        model = Admission


class DeleteAdmissionMutation(DjangoDeleteMutation):
    class Meta:
        model = Admission


class ObfuscateAdmissionMutation(graphene.Mutation):
    class Arguments:
        pass

    ok = graphene.Boolean()

    def mutate(self, info, *args, **kwargs):
        admission = Admission.get_active_admission()
        if not admission:
            return ObfuscateAdmissionMutation(ok=False)

        obfuscate_admission(admission)
        return ObfuscateAdmissionMutation(ok=True)


# === Interview ===
class GenerateInterviewsMutation(graphene.Mutation):
    ok = graphene.Boolean()
    interviews_generated = graphene.Int()

    def mutate(self, info, *args, **kwargs):
        # retrieve the schedule template
        schedule = (
            InterviewScheduleTemplate.objects.all().first()
        )  # should handle this a bit better probably
        generate_interviews_from_schedule(schedule)
        num = Interview.objects.all().count()

        return GenerateInterviewsMutation(ok=True, interviews_generated=num)


class DeleteAllInterviewsMutation(graphene.Mutation):
    count = graphene.Int()

    def mutate(self, info, *args, **kwargs):
        admission = Admission.get_active_admission()
        if admission.status == AdmissionStatus.OPEN.value:
            raise SuspiciousOperation("Admission is open, cannot delete")
        interviews = Interview.objects.all().all()
        count = interviews.count()
        interviews.delete()
        return DeleteAllInterviewsMutation(count=count)


# === InterviewLocation ===
class CreateInterviewLocationMutation(DjangoCreateMutation):
    class Meta:
        model = InterviewLocation


class DeleteInterviewLocationMutation(DjangoDeleteMutation):
    class Meta:
        model = InterviewLocation
        exclude_fields = ("order",)


# === InterviewLocationAvailability ===
class CreateInterviewLocationAvailability(DjangoCreateMutation):
    class Meta:
        model = InterviewLocationAvailability


class DeleteInterviewLocationAvailabilityMutation(DjangoDeleteMutation):
    class Meta:
        model = InterviewLocationAvailability


# === InterviewScheduleTemplate ===
class PatchInterviewScheduleTemplateMutation(DjangoPatchMutation):
    class Meta:
        model = InterviewScheduleTemplate


# === InterviewBooleanEvaluation ===
class CreateInterviewBooleanEvaluationMutation(DjangoCreateMutation):
    class Meta:
        model = InterviewBooleanEvaluation
        exclude_fields = ("order",)

    @classmethod
    def before_mutate(cls, root, info, input):
        increment = (
            InterviewBooleanEvaluation.objects.all().order_by(("order")).last().order
            + 1
        )
        input["order"] = increment
        return input


class PatchInterviewBooleanEvaluationMutation(DjangoPatchMutation):
    class Meta:
        model = InterviewBooleanEvaluation


class DeleteInterviewBooleanEvaluationMutation(DjangoDeleteMutation):
    class Meta:
        model = InterviewBooleanEvaluation


# === InterviewAdditionalEvaluationStatement ===
class CreateInterviewAdditionalEvaluationStatementMutation(DjangoCreateMutation):
    class Meta:
        model = InterviewAdditionalEvaluationStatement
        exclude_fields = ("order",)


class PatchInterviewAdditionalEvaluationStatementMutation(DjangoPatchMutation):
    class Meta:
        model = InterviewAdditionalEvaluationStatement


class DeleteInterviewAdditionalEvaluationStatementMutation(DjangoDeleteMutation):
    class Meta:
        model = InterviewAdditionalEvaluationStatement


# === AdmissionAvailableInternalGroupPositionData ===
class CreateAdmissionAvailableInternalGroupPositionData(DjangoCreateMutation):
    class Meta:
        model = AdmissionAvailableInternalGroupPositionData
        exclude_fields = ("admission",)

    @classmethod
    def before_mutate(cls, root, info, input):
        admission_id = Admission.get_active_admission().id
        input["admission"] = admission_id
        return input


class PatchAdmissionAvailableInternalGroupPositionData(DjangoPatchMutation):
    class Meta:
        model = AdmissionAvailableInternalGroupPositionData


class DeleteAdmissionAvailableInternalGroupPositionData(DjangoDeleteMutation):
    class Meta:
        model = AdmissionAvailableInternalGroupPositionData


class AdmissionsMutations(graphene.ObjectType):
    create_applicant = CreateApplicantMutation.Field()
    patch_applicant = PatchApplicantMutation.Field()
    delete_applicant = DeleteApplicantMutation.Field()

    create_applications = CreateApplicationsMutation.Field()

    create_admission = CreateAdmissionMutation.Field()
    patch_admission = PatchAdmissionMutation.Field()
    delete_admission = DeleteAdmissionMutation.Field()

    patch_interview_schedule_template = PatchInterviewScheduleTemplateMutation.Field()
    create_interview_location_availability = CreateInterviewLocationAvailability.Field()
    delete_interview_location_availability = (
        DeleteInterviewLocationAvailabilityMutation.Field()
    )

    create_interview_location = CreateInterviewLocationMutation.Field()
    delete_interview_location = DeleteInterviewLocationMutation.Field()

    create_interview_boolean_evaluation = (
        CreateInterviewBooleanEvaluationMutation.Field()
    )
    delete_interview_boolean_evaluation = (
        DeleteInterviewBooleanEvaluationMutation.Field()
    )
    patch_interview_boolean_evaluation = PatchInterviewBooleanEvaluationMutation.Field()

    create_interview_additional_evaluation_statement = (
        CreateInterviewAdditionalEvaluationStatementMutation.Field()
    )
    delete_interview_additional_evaluation_statement = (
        DeleteInterviewAdditionalEvaluationStatementMutation.Field()
    )
    patch_interview_additional_evaluation_statement = (
        PatchInterviewAdditionalEvaluationStatementMutation.Field()
    )
    patch_admission_available_internal_group_position_data = (
        PatchAdmissionAvailableInternalGroupPositionData.Field()
    )
    create_admission_available_internal_group_position_data = (
        CreateAdmissionAvailableInternalGroupPositionData.Field()
    )
    delete_admission_available_internal_group_position_data = (
        DeleteAdmissionAvailableInternalGroupPositionData.Field()
    )

    re_send_application_token = ResendApplicantTokenMutation.Field()
    generate_interviews = GenerateInterviewsMutation.Field()
    obfuscate_admission = ObfuscateAdmissionMutation.Field()
    delete_all_interviews = DeleteAllInterviewsMutation.Field()
