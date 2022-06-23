import datetime
import graphene
from graphene import Node
from graphql_relay import to_global_id
from graphene_django import DjangoObjectType
from django.db import IntegrityError
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from django.conf import settings
from common.util import date_time_combiner
from django.db.models import Q
from graphene_django.filter import DjangoFilterConnectionField
from admissions.utils import (
    generate_interviews_from_schedule,
    resend_auth_token_email,
    obfuscate_admission,
    group_interviews_by_date,
    create_interview_slots,
    mass_send_welcome_to_interview_email,
    internal_group_applicant_data,
    admission_applicant_preview,
    get_admission_final_applicant_qs,
    get_applicant_offered_position,
)
from django.core.exceptions import SuspiciousOperation
from django.utils import timezone
from admissions.models import (
    Applicant,
    ApplicantInterest,
    Admission,
    AdmissionAvailableInternalGroupPositionData,
    InternalGroupPositionPriority,
    Interview,
    InterviewLocation,
    InterviewLocationAvailability,
    InterviewScheduleTemplate,
    InterviewBooleanEvaluation,
    InterviewAdditionalEvaluationStatement,
    InterviewBooleanEvaluationAnswer,
    InterviewAdditionalEvaluationAnswer,
)
from organization.models import (
    InternalGroupPosition,
    InternalGroup,
    InternalGroupPositionMembership,
)
from organization.schema import InternalGroupPositionNode, InternalGroupNode
from admissions.filters import AdmissionFilter
from admissions.consts import (
    AdmissionStatus,
    Priority,
    ApplicantStatus,
    InternalGroupStatus,
)
from graphene_django_cud.types import TimeDelta
from graphene import Time, Date
from graphene_django_cud.util import disambiguate_id
from users.schema import UserNode
from users.models import User
from economy.models import SociBankAccount


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


class ApplicantInterestNode(DjangoObjectType):
    class Meta:
        model = ApplicantInterest
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return ApplicantInterest.objects.get(pk=id)


class ApplicantNode(DjangoObjectType):
    class Meta:
        model = Applicant
        interfaces = (Node,)

    full_name = graphene.String(source="get_full_name")
    priorities = graphene.List(InternalGroupPositionPriorityNode)
    internal_group_interests = graphene.List(ApplicantInterestNode)

    interviewer_from_internal_group = graphene.ID(internal_group_id=graphene.ID())

    def resolve_internal_group_interests(self: Applicant, info, *args, **kwargs):
        return self.internal_group_interests.all()

    def resolve_interviewer_from_internal_group(
        self: Applicant, info, internal_group_id, *args, **kwargs
    ):
        """
        We want to be able to query whether or not there is an interviewer from the respective internal
        group set up for the given interview. If it exists we return the id so we can determine what piece
        of UI we want to render in react.
            > If None the interview isn't covered
            > If ID it is covered but we want to render differently based on who is logged in
        """
        internal_group_id = disambiguate_id(internal_group_id)
        internal_group = InternalGroup.objects.filter(id=internal_group_id).first()
        interview = self.interview

        if not internal_group or not interview:
            return None

        interviewers = interview.interviewers.all()
        interviewer_from_internal_group = interviewers.filter(
            internal_group_position_history__date_ended__isnull=True,
            internal_group_position_history__position__internal_group=internal_group,
        ).first()  # We assume that we have constraint that only allows interviewer from one internal group

        if not interviewer_from_internal_group:
            return None

        return to_global_id("UserNode", interviewer_from_internal_group.id)

    def resolve_priorities(self: Applicant, info, *args, **kwargs):
        first_priority = self.priorities.filter(
            applicant_priority=Priority.FIRST
        ).first()
        second_priority = self.priorities.filter(
            applicant_priority=Priority.SECOND
        ).first()
        third_priority = self.priorities.filter(
            applicant_priority=Priority.THIRD
        ).first()
        return [first_priority, second_priority, third_priority]

    def resolve_image(self: Applicant, info, **kwargs):
        if self.image:
            return f"{settings.HOST_URL}{self.image.url}"
        else:
            return None

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


class AdditionalEvaluationAnswerEnum(graphene.Enum):
    VERY_LITTLE = "VERY"
    LITTLE = "LITTLE"
    MEDIUM = "MEDIUM"
    SOMEWHAT = "SOMEWHAT"
    VERY = "VERY"


class InterviewBooleanEvaluationAnswerNode(DjangoObjectType):
    class Meta:
        model = InterviewBooleanEvaluationAnswer
        interfaces = (Node,)


class InterviewAdditionalEvaluationAnswerNode(DjangoObjectType):
    class Meta:
        model = InterviewAdditionalEvaluationAnswer
        interfaces = (Node,)


class InterviewNode(DjangoObjectType):
    class Meta:
        model = Interview
        interfaces = (Node,)

    interviewers = graphene.List(UserNode)
    boolean_evaluation_answers = graphene.List(InterviewBooleanEvaluationAnswerNode)
    additional_evaluation_answers = graphene.List(
        InterviewAdditionalEvaluationAnswerNode
    )

    def resolve_boolean_evaluation_answers(self: Interview, info, *args, **kwargs):
        return self.boolean_evaluation_answers.all().order_by("statement__order")

    def resolve_additional_evaluation_answers(self: Interview, info, *args, **kwargs):
        return self.additional_evaluation_answers.all().order_by("statement__order")

    def resolve_interviewers(self: Interview, info, *args, **kwargs):
        return self.interviewers.all()

    @classmethod
    def get_node(cls, info, id):
        return Interview.objects.get(pk=id)


class InternalGroupApplicantsData(graphene.ObjectType):
    """
    A way to encapsulate the applicants for a given internal group.
    """

    internal_group = graphene.Field(InternalGroupNode)
    # This should probably be InternalGroupPositionPriority objects instead
    # and then we access the applicant data from there instead
    first_priorities = graphene.List(ApplicantNode)
    second_priorities = graphene.List(ApplicantNode)
    third_priorities = graphene.List(ApplicantNode)

    positions_to_fill = graphene.Int()
    # How far they have come in their process
    current_progress = graphene.Int()


class InternalGroupDiscussionData(graphene.ObjectType):
    internal_group = graphene.Field(InternalGroupNode)
    processed_applicants = graphene.List(InternalGroupPositionPriorityNode)
    applicants_open_for_other_positions = graphene.List(ApplicantNode)
    applicants = graphene.List(ApplicantNode)


class CloseAdmissionQueryData(graphene.ObjectType):
    valid_applicants = graphene.List(ApplicantNode)
    applicant_interests = graphene.List(ApplicantInterestNode)


class ApplicantQuery(graphene.ObjectType):
    applicant = Node.Field(ApplicantNode)
    all_applicants = graphene.List(ApplicantNode)
    get_applicant_from_token = graphene.Field(ApplicantNode, token=graphene.String())
    internal_group_applicants_data = graphene.Field(
        InternalGroupApplicantsData, internal_group=graphene.ID()
    )
    all_internal_group_applicant_data = graphene.List(InternalGroupApplicantsData)
    internal_group_discussion_data = graphene.Field(
        InternalGroupDiscussionData, internal_group_id=graphene.ID(required=True)
    )
    valid_applicants = graphene.Field(CloseAdmissionQueryData)

    def resolve_valid_applicants(self, info, *args, **kwargs):
        # Can we do an annotation here? Kind of like unwanted = all_priorities = DO_NOT_WANT
        valid_applicants = (
            Applicant.objects.filter(
                priorities__internal_group_priority__in=[
                    InternalGroupStatus.WANT,
                    InternalGroupStatus.RESERVE,
                    InternalGroupStatus.PROBABLY_WANT,
                ],
                status=ApplicantStatus.INTERVIEW_FINISHED,
            )
            .order_by("first_name")
            .distinct()
        )

        print(valid_applicants)
        active_admissions = Admission.get_active_admission()
        applicant_interests = ApplicantInterest.objects.filter(
            applicant__admission=active_admissions
        ).order_by("applicant__first_name")

        return CloseAdmissionQueryData(
            valid_applicants=valid_applicants, applicant_interests=applicant_interests
        )

    def resolve_get_applicant_from_token(self, info, token, *args, **kwargs):
        applicant = Applicant.objects.filter(token=token).first()
        return applicant

    def resolve_all_applicants(self, info, *args, **kwargs):
        return Applicant.objects.all().order_by("first_name")

    def resolve_internal_group_applicants_data(
        self, info, internal_group, *args, **kwargs
    ):
        django_id = disambiguate_id(internal_group)
        internal_group = InternalGroup.objects.filter(id=django_id).first()
        if not internal_group:
            return None

        data = internal_group_applicant_data(internal_group)
        return data

    def resolve_all_internal_group_applicant_data(self, info, *args, **kwargs):
        admission = Admission.get_active_admission()
        positions = admission.available_internal_group_positions.all()
        internal_groups = InternalGroup.objects.filter(positions__in=positions)

        internal_group_data = []
        for internal_group in internal_groups:
            data = internal_group_applicant_data(internal_group)
            internal_group_data.append(data)

        return internal_group_data

    def resolve_internal_group_discussion_data(
        self, info, internal_group_id, *args, **kwargs
    ):
        """
        Resolves data for the discussion view for a given internal group. This includes fields
        with all applicants having applied to this internal group, filtering of processed
        applicants and in the future other metrics like progress and remaining applicants
        to evaluate.

        """
        internal_group_id = disambiguate_id(internal_group_id)
        internal_group = InternalGroup.objects.filter(id=internal_group_id).first()

        if not internal_group:
            return None

        # We want to return and filter this instead
        all_internal_group_priorities = InternalGroupPositionPriority.objects.filter(
            internal_group_position__internal_group=internal_group,
            applicant__interview__isnull=False,
        ).order_by("applicant__first_name")

        # This can be a simplified data model in the future
        processed_applicants = all_internal_group_priorities.filter(
            internal_group_priority__in=[
                InternalGroupStatus.WANT,
                InternalGroupStatus.DO_NOT_WANT,
            ]
        )

        # All applicants that have applied to this internal group and finished their interview
        applicants = Applicant.objects.filter(
            priorities__internal_group_position__internal_group=internal_group,
            status=ApplicantStatus.INTERVIEW_FINISHED,
        ).distinct()

        # Also throw in applicants open for other positions.
        applicants_open_for_other_positions = (
            Applicant.objects.filter(
                open_for_other_positions=True,
                status=ApplicantStatus.INTERVIEW_FINISHED,
            )
            .exclude(pk__in=applicants)
            .distinct()
        )

        return InternalGroupDiscussionData(
            internal_group=internal_group,
            processed_applicants=processed_applicants,
            applicants_open_for_other_positions=applicants_open_for_other_positions,
            applicants=applicants,
        )


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


class CreateApplicationsMutation(graphene.Mutation):
    class Arguments:
        emails = graphene.List(graphene.String)

    ok = graphene.Boolean()
    applications_created = graphene.Int()
    faulty_emails = graphene.List(graphene.String)

    def mutate(self, info, emails):
        faulty_emails = []
        registered_emails = []
        for email in emails:
            try:
                Applicant.create_or_update_application(email)
                registered_emails.append(email)
            except IntegrityError:
                faulty_emails.append(email)

        mass_send_welcome_to_interview_email(registered_emails)
        return CreateApplicationsMutation(
            ok=True,
            applications_created=len(emails) - len(faulty_emails),
            faulty_emails=faulty_emails,
        )


class ApplicantPreview(graphene.ObjectType):
    class ApplicantPriorityEnum(graphene.Enum):
        FIRST = "FIRST"
        SECOND = "SECOND"
        THIRD = "THIRD"
        NA = "N/A"

    full_name = graphene.String()
    id = graphene.GlobalID()
    offered_internal_group_position_name = graphene.String()
    applicant_priority = graphene.String()
    phone = graphene.String()


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
    internal_group_positions_available_for_applicants = graphene.List(
        InternalGroupPositionNode
    )
    current_admission_internal_group_position_data = graphene.List(
        AdmissionAvailableInternalGroupPositionDataNode
    )
    internal_groups_accepting_applicants = graphene.List(InternalGroupNode)

    admission_applicants_preview = graphene.List(ApplicantPreview)

    def resolve_admission_applicants_preview(self, info, *args, **kwargs):
        admission = Admission.get_active_admission()
        final_applicant_preview = admission_applicant_preview(admission)
        return final_applicant_preview

    def resolve_current_admission_internal_group_position_data(
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

    # Intended use for admission configuration
    def resolve_externally_available_internal_group_positions(
        self, info, *args, **kwargs
    ):
        return InternalGroupPosition.objects.filter(available_externally=True).order_by(
            "name"
        )

    def resolve_internal_groups_accepting_applicants(self, info, *args, **kwargs):
        admission = Admission.get_active_admission()
        if not admission:
            return []
        return admission.internal_groups_accepting_applicants()

    def resolve_internal_group_positions_available_for_applicants(
        self, info, *args, **kwargs
    ):
        admission = Admission.get_active_admission()
        if not admission:
            return []
        return admission.available_internal_group_positions.all().order_by("name")


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


class InterviewSlot(graphene.ObjectType):
    interview_start = graphene.DateTime()
    interview_ids = graphene.List(graphene.ID)


class AvailableInterviewsDayGrouping(graphene.ObjectType):
    date = graphene.Date()
    interview_slots = graphene.List(InterviewSlot)


class InterviewQuery(graphene.ObjectType):
    interview = Node.Field(InterviewNode)
    interview_template = graphene.Field(InterviewTemplate)
    interviews_available_for_booking = graphene.List(
        AvailableInterviewsDayGrouping, day_offset=graphene.Int(required=True)
    )

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

    def resolve_interviews_available_for_booking(
        self, info, day_offset, *args, **kwargs
    ):
        """
        The idea here is that we want to parse interviews in such a way that we only return
        a timestamp for when the interview starts, and a list of ids for interviews that
        are available for booking. This gives us a bit of security because if the interview
        is available and an applicant tries to book the same as another one they can just
        try one of the other interviews.
        """
        # We get all interviews available for booking
        now = timezone.datetime.now()
        cursor = timezone.make_aware(
            timezone.datetime(  # Use midnight helper here
                year=now.year, month=now.month, day=now.day, hour=0, minute=0, second=0
            )
            + timezone.timedelta(days=1)
        )
        cursor += timezone.timedelta(days=day_offset)
        cursor_offset = cursor + timezone.timedelta(days=2)
        available_interviews = Interview.objects.filter(
            applicant__isnull=True,
            interview_start__gte=cursor,
            interview_start__lte=cursor_offset,
        )

        available_interviews_timeslot_grouping = []
        parsed_interviews = create_interview_slots(
            group_interviews_by_date(available_interviews)
        )

        for day in parsed_interviews:
            timeslots = []
            for grouping in day["groupings"]:
                interviews = grouping["interviews"]
                interview_ids = [
                    to_global_id("InterviewNode", interview.id)
                    for interview in interviews
                ]
                timeslots.append(
                    InterviewSlot(
                        interview_start=grouping["timestamp"],
                        interview_ids=interview_ids,
                    )
                )
            available_interviews_timeslot_grouping.append(
                AvailableInterviewsDayGrouping(
                    date=day["date"], interview_slots=timeslots
                )
            )
        return available_interviews_timeslot_grouping


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


class ToggleApplicantWillBeAdmittedMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    def mutate(self, info, id, *args, **kwargs):
        applicant_id = disambiguate_id(id)
        applicant = Applicant.objects.filter(id=applicant_id).first()

        if not applicant:
            return ToggleApplicantWillBeAdmittedMutation(success=False)

        applicant.will_be_admitted = not applicant.will_be_admitted
        applicant.save()
        return ToggleApplicantWillBeAdmittedMutation(success=True)


# === ApplicantInterest ===
class CreateApplicantInterestMutation(DjangoCreateMutation):
    class Meta:
        model = ApplicantInterest


class DeleteApplicantInterestMutation(DjangoDeleteMutation):
    class Meta:
        model = ApplicantInterest


class GiveApplicantToInternalGroupMutation(graphene.Mutation):
    class Arguments:
        applicant_interest_id = graphene.ID(required=True)

    success = graphene.NonNull(graphene.Boolean)

    def mutate(self, info, applicant_interest_id, *args, **kwargs):
        applicant_interest_id = disambiguate_id(applicant_interest_id)
        applicant_interest = ApplicantInterest.objects.get(pk=applicant_interest_id)

        # There exists a row for each interest between an InternalGroup and an Applicant
        # meaning we can use the InternalGroup accessed from the interest instance
        internal_group = applicant_interest.internal_group
        admission = Admission.get_active_admission()

        # DANGER: If an internal group has more than one position available externally
        # this could lead to some obscure bugs.
        inferred_offered_positions = (
            admission.available_internal_group_positions.filter(
                internal_group=internal_group
            )
        )

        # Raise an error so its easier to catch if this happens and we should do something
        # about this in the future.
        # Famous last words Alexander Orvik 23.06.2022
        if inferred_offered_positions.count() > 1:
            raise Exception(
                "Internal group has more than two positions available externally"
            )

        position = inferred_offered_positions.first()
        applicant_interest.position_to_be_offered = position
        applicant_interest.save()

        # We have given away the applicant. Now we need to reset any other offers
        applicant = applicant_interest.applicant
        for interest in applicant.internal_group_interests.all():
            if interest == applicant_interest:
                # Should not reset the one we just changed
                continue
            interest.position_to_be_offered = None
            interest.save()

        return GiveApplicantToInternalGroupMutation(success=True)


# === InternalGroupPositionPriority ===
class AddInternalGroupPositionPriorityMutation(graphene.Mutation):
    class Arguments:
        internal_group_position_id = graphene.ID(required=True)
        applicant_id = graphene.ID(required=True)

    success = graphene.Boolean()

    def mutate(self, info, internal_group_position_id, applicant_id, *args, **kwargs):
        internal_group_position_id = disambiguate_id(internal_group_position_id)
        applicant_id = disambiguate_id(applicant_id)
        internal_group_position = InternalGroupPosition.objects.filter(
            id=internal_group_position_id
        ).first()
        applicant = Applicant.objects.filter(id=applicant_id).first()

        if not (internal_group_position and applicant):
            return AddInternalGroupPositionPriorityMutation(success=False)

        applicant.add_priority(internal_group_position)
        return AddInternalGroupPositionPriorityMutation(success=True)


class PatchInternalGroupPositionPriority(DjangoPatchMutation):
    class Meta:
        model = InternalGroupPositionPriority


class DeleteInternalGroupPositionPriority(DjangoDeleteMutation):
    class Meta:
        model = InternalGroupPositionPriority

    @classmethod
    def before_save(cls, root, info, id, obj):
        # We need to re-order the priorities in case something is deleted out of order
        priorities = [Priority.FIRST, Priority.SECOND, Priority.THIRD]
        applicant = obj.applicant
        unfiltered_priorities = applicant.get_priorities
        filtered_priorities = []
        # Unfiltered priorities can have None values. Get rid of them
        for priority in unfiltered_priorities:
            if not priority:
                continue
            # We don't want to re-add the position we are trying to delete
            if priority.internal_group_position == obj.internal_group_position:
                continue

            filtered_priorities.append(priority.internal_group_position)

        # Delete the priorities so we can add them in the right order
        applicant.priorities.all().delete()
        for index, position in enumerate(filtered_priorities):
            priority = priorities[index]
            applicant.priorities.add(
                InternalGroupPositionPriority.objects.create(
                    applicant=applicant,
                    internal_group_position=position,
                    applicant_priority=priority,
                )
            )
        return obj


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


class LockAdmissionMutation(graphene.Mutation):
    # Final stage before we decide who is admitted into KSG.
    # Requires that all applicants have been evaluated in som manner
    admission = graphene.Field(AdmissionNode)

    def mutate(self, info, *args, **kwargs):
        admission = Admission.get_active_admission()
        unevaluated_applicants = admission.applicants.filter(
            priorities__internal_group_priority__isnull=True,
            status=ApplicantStatus.INTERVIEW_FINISHED,
        )
        if unevaluated_applicants.count() > 0:
            raise Exception("All valid applicants have not been considered")

        admission.status = AdmissionStatus.LOCKED
        admission.save()
        return LockAdmissionMutation(admission=admission)


class CloseAdmissionMutation(graphene.Mutation):
    failed_user_generation = graphene.List(ApplicantNode)

    def mutate(self, info, *args, **kwargs):
        """
        1. Get all applicants we have marked for admission or with and
           offer from an internal group
        2. Create a user instance for all of them with their data
        3. Give them the internal group position they were admitted for
        4. obfuscate identifying applicant information
        5. Close the admission
        """
        # Step 1)
        admission = Admission.get_active_admission()
        admitted_applicants = get_admission_final_applicant_qs(admission)
        failed_user_generation = []

        for applicant in admitted_applicants:
            try:
                # Step 2)
                applicant_user_profile = User.objects.create(
                    username=applicant.email,
                    first_name=applicant.first_name,
                    last_name=applicant.last_name,
                    email=applicant.email,
                    profile_image=applicant.image,
                    phone=applicant.phone,
                    start_ksg=datetime.datetime.today(),
                    study_address=applicant.address,
                    home_address=applicant.hometown,
                    study=applicant.study,
                    date_of_birth=applicant.date_of_birth,
                )
                """
                Unique constraints can be fucked up here
                    1. How should we handle emails? Do this at applicant stage?
                    2. Phone number 
                """
                # Step 3)
                # We give the applicant the internal group position they have been accepted into
                internal_group_position = get_applicant_offered_position(applicant)
                internal_group_position = internal_group_position
                InternalGroupPositionMembership.objects.create(
                    position=internal_group_position,
                    user=applicant_user_profile,
                    date_joined=datetime.date.today(),
                )

                SociBankAccount.objects.create(
                    user=applicant_user_profile, balance=0, card_uuid=None
                )

            except Exception as e:
                # Should we write this out to some model or a log?
                failed_user_generation.append(applicant)

        # Step 4)
        # User generation is done. Now we want to remove all identifying information
        obfuscate_admission(admission)

        # Step 5)
        # It's a wrap folks
        admission.status = AdmissionStatus.CLOSED
        admission.save()
        admitted_applicants.update(will_be_admitted=False)
        return CloseAdmissionMutation(failed_user_generation=failed_user_generation)


# === Interview ===
class GenerateInterviewsMutation(graphene.Mutation):
    ok = graphene.Boolean()
    interviews_generated = graphene.Int()

    def mutate(self, info, *args, **kwargs):
        # retrieve the schedule template
        schedule = InterviewScheduleTemplate.objects.all().first()
        # should handle this a bit better probably
        generate_interviews_from_schedule(schedule)
        num = Interview.objects.all().count()
        return GenerateInterviewsMutation(ok=True, interviews_generated=num)


class SetSelfAsInterviewerMutation(graphene.Mutation):
    class Arguments:
        interview_id = graphene.ID(required=True)

    success = graphene.Boolean()

    def mutate(self, info, interview_id, *args, **kwargs):
        interview_django_id = disambiguate_id(interview_id)
        interview = Interview.objects.filter(pk=interview_django_id).first()
        if not interview:
            return SetSelfAsInterviewerMutation(success=False)

        # ToDo:
        # Interview exists. Here we can parse whether or not a person from this internal group is here already as well

        user = info.context.user
        existing_interviewers = interview.interviewers.all()
        if user in existing_interviewers:
            # User is already on this interview
            return SetSelfAsInterviewerMutation(success=True)

        interview.interviewers.add(user)
        interview.save()
        return SetSelfAsInterviewerMutation(success=True)


class PatchInterviewMutation(DjangoPatchMutation):
    class Meta:
        model = Interview
        one_to_one_extras = {
            "applicant": {"type": "InterviewPatchApplicantInput", "operation": "patch"}
        }


class RemoveSelfAsInterviewerMutation(graphene.Mutation):
    class Arguments:
        interview_id = graphene.ID(required=True)

    success = graphene.Boolean()

    def mutate(self, info, interview_id, *args, **kwargs):
        interview_django_id = disambiguate_id(interview_id)
        interview = Interview.objects.filter(id=interview_django_id).first()
        if not interview:
            return RemoveSelfAsInterviewerMutation(success=False)

        user = info.context.user
        interviewers = interview.interviewers.all()
        interview.interviewers.set(interviewers.exclude(id=user.id))
        interview.save()
        return RemoveSelfAsInterviewerMutation(success=True)


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


class BookInterviewMutation(graphene.Mutation):
    class Arguments:
        interview_ids = graphene.List(graphene.ID)
        applicant_token = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, interview_ids, applicant_token, *args, **kwargs):
        applicant = Applicant.objects.get(token=applicant_token)
        if getattr(applicant, "interview", None):
            raise SuspiciousOperation("Applicant already has an interview")

        for interview_id in interview_ids:
            try:
                django_id = disambiguate_id(interview_id)
                interview = Interview.objects.get(pk=django_id)

                interview.applicant = applicant
                interview.save()
                applicant.status = ApplicantStatus.SCHEDULED_INTERVIEW.value
                applicant.save()
                return BookInterviewMutation(ok=True)

            except IntegrityError:  # Someone already booked this interview
                pass
            except Interview.DoesNotExist:
                pass
            except Applicant.DoesNotExist:
                return BookInterviewMutation(ok=False)

        return BookInterviewMutation(ok=False)


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
        count = InterviewBooleanEvaluation.objects.all().count()
        increment = count + 1
        input["order"] = increment
        return input


class PatchInterviewBooleanEvaluationMutation(DjangoPatchMutation):
    class Meta:
        model = InterviewBooleanEvaluation


class PatchInterviewBooleanEvaluationAnswerMutation(DjangoPatchMutation):
    class Meta:
        model = InterviewBooleanEvaluationAnswer


class DeleteInterviewBooleanEvaluationMutation(DjangoDeleteMutation):
    class Meta:
        model = InterviewBooleanEvaluation


# === InterviewAdditionalEvaluationStatement ===
class CreateInterviewAdditionalEvaluationStatementMutation(DjangoCreateMutation):
    class Meta:
        model = InterviewAdditionalEvaluationStatement
        exclude_fields = ("order",)

    @classmethod
    def before_mutate(cls, root, info, input):
        count = InterviewAdditionalEvaluationStatement.objects.all().count()
        increment = count + 1
        input["order"] = increment
        return input


# === InterviewAdditionalEvaluationAnswer ===
class PatchInterviewAdditionalEvaluationAnswer(DjangoPatchMutation):
    class Meta:
        model = InterviewAdditionalEvaluationAnswer


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

    create_applicant_interest = CreateApplicantInterestMutation.Field()
    delete_applicant_interest = DeleteApplicantInterestMutation.Field()

    give_applicant_to_internal_group = GiveApplicantToInternalGroupMutation.Field()

    create_applications = CreateApplicationsMutation.Field()

    create_admission = CreateAdmissionMutation.Field()
    patch_admission = PatchAdmissionMutation.Field()
    delete_admission = DeleteAdmissionMutation.Field()

    patch_interview_schedule_template = PatchInterviewScheduleTemplateMutation.Field()
    create_interview_location_availability = CreateInterviewLocationAvailability.Field()
    delete_interview_location_availability = (
        DeleteInterviewLocationAvailabilityMutation.Field()
    )

    patch_interview = PatchInterviewMutation.Field()

    create_interview_location = CreateInterviewLocationMutation.Field()
    delete_interview_location = DeleteInterviewLocationMutation.Field()

    create_interview_boolean_evaluation = (
        CreateInterviewBooleanEvaluationMutation.Field()
    )
    delete_interview_boolean_evaluation = (
        DeleteInterviewBooleanEvaluationMutation.Field()
    )
    patch_interview_boolean_evaluation = PatchInterviewBooleanEvaluationMutation.Field()
    patch_interview_boolean_evaluation_answer = (
        PatchInterviewBooleanEvaluationAnswerMutation.Field()
    )

    patch_interview_additional_evaluation_answer = (
        PatchInterviewAdditionalEvaluationAnswer.Field()
    )

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
    book_interview = BookInterviewMutation.Field()
    delete_all_interviews = DeleteAllInterviewsMutation.Field()
    set_self_as_interviewer = SetSelfAsInterviewerMutation.Field()
    remove_self_as_interviewer = RemoveSelfAsInterviewerMutation.Field()
    toggle_applicant_will_be_admitted = ToggleApplicantWillBeAdmittedMutation.Field()
    lock_admission = LockAdmissionMutation.Field()
    close_admission = CloseAdmissionMutation.Field()

    add_internal_group_position_priority = (
        AddInternalGroupPositionPriorityMutation.Field()
    )
    patch_internal_group_position_priority = PatchInternalGroupPositionPriority.Field()
    delete_internal_group_position_priority = (
        DeleteInternalGroupPositionPriority.Field()
    )
