import datetime
from secrets import token_urlsafe

import bleach
import graphene
from graphene import Node
from graphql_relay import to_global_id
from graphene_django import DjangoObjectType
from django.db import IntegrityError, transaction
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_file_upload.scalars import Upload

from common.consts import BLEACH_ALLOWED_TAGS
from common.decorators import gql_has_permissions
from common.util import (
    date_time_combiner,
    compress_image,
    midnight_timestamps_from_date,
)
from django.db.models import Q, Case, When, Value
from graphene_django.filter import DjangoFilterConnectionField
from admissions.utils import (
    generate_interviews_from_schedule,
    resend_auth_token_email,
    obfuscate_admission,
    group_interviews_by_date,
    create_interview_slots,
    internal_group_applicant_data,
    admission_applicant_preview,
    get_admission_final_applicant_qs,
    get_applicant_offered_position,
    read_admission_csv,
    send_applicant_notice_email,
    send_new_interview_mail,
    send_interview_cancelled_email,
    notify_interviewers_cancelled_interview_email,
    send_interview_confirmation_email,
    remove_applicant_choice,
    construct_new_priority_list,
    interview_overview_parser,
    notify_interviewers_applicant_has_been_removed_from_interview_email,
    get_interview_statistics,
)
from django.core.exceptions import SuspiciousOperation, ValidationError
from django.utils import timezone
from admissions.models import (
    Applicant,
    ApplicantComment,
    ApplicantInterest,
    ApplicantRecommendation,
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
from organization.consts import InternalGroupPositionMembershipType
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


class ApplicantNoticeMethodEnum(graphene.Enum):
    EMAIL = "email"
    CALL = "call"


class ApplicantCommentNode(DjangoObjectType):
    class Meta:
        model = ApplicantComment
        interfaces = (Node,)

    @classmethod
    @gql_has_permissions("admissions.view_applicantcomment")
    def get_node(cls, info, id):
        return ApplicantComment.objects.get(pk=id)


class ApplicantRecommendationNode(DjangoObjectType):
    class Meta:
        model = ApplicantRecommendation
        interfaces = (Node,)

    @classmethod
    @gql_has_permissions("admissions.view_applicantrecommendation")
    def get_node(cls, info, id):
        return ApplicantRecommendation.objects.get(pk=id)


class ApplicantNode(DjangoObjectType):
    class Meta:
        model = Applicant
        interfaces = (Node,)

    full_name = graphene.String(source="get_full_name")
    priorities = graphene.List(InternalGroupPositionPriorityNode)
    internal_group_interests = graphene.List(ApplicantInterestNode)

    interviewer_from_internal_group = graphene.ID(internal_group_id=graphene.ID())
    interview_is_covered = graphene.Boolean(internal_group_id=graphene.ID())
    notice_method = ApplicantNoticeMethodEnum()
    comments = graphene.List(ApplicantCommentNode)

    i_am_attending_interview = graphene.Boolean()

    def resolve_i_am_attending_interview(self: Applicant, info, *args, **kwargs):
        user = info.context.user
        if not user:
            return False
        interview = self.interview
        if not interview:
            return False

        interviewers = interview.interviewers
        return interviewers.filter(pk=user.id).exists()

    def resolve_interview_is_covered(
        self: Applicant, info, internal_group_id, *args, **kwargs
    ):
        internal_group_id = disambiguate_id(internal_group_id)
        internal_group = InternalGroup.objects.get(id=internal_group_id)

        interview = self.interview

        if not interview:
            return False

        interviewers = interview.interviewers.all()
        interviewers_from_internal_group = interviewers.filter(
            internal_group_position_history__date_ended__isnull=True,
            internal_group_position_history__position__internal_group=internal_group,
        )

        applicant = interview.get_applicant
        # Should never happen
        if not applicant:
            return False

        priorities = applicant.get_priorities
        # filter none values
        priorities = [priority for priority in priorities if priority]

        if interviewers_from_internal_group:
            # Edge case where we do not want to mark it as covered.
            if len(priorities) == 1 and interviewers.count() < 2:
                return False
            return True

        return False

    def resolve_comments(self: Applicant, info, **kwargs):
        return self.comments.all().order_by("created_at")

    def resolve_internal_group_interests(self: Applicant, info, *args, **kwargs):
        return self.internal_group_interests.all()

    # This will be deprecated
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
            return f"{self.image.url}"
        else:
            return None

    @classmethod
    @gql_has_permissions("admissions.view_applicant")
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

    class MembershipType(graphene.Enum):
        GANG_MEMBER = InternalGroupPositionMembershipType.GANG_MEMBER
        FUNCTIONARY = InternalGroupPositionMembershipType.FUNCTIONARY

    membership_type = MembershipType()

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

    interview_booking_late_batch_time = graphene.Time()
    interview_booking_override_delta = TimeDelta()

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

    def resolve_interview_booking_late_batch_time(
        self: Admission, info, *args, **kwargs
    ):
        return self.interview_booking_late_batch_time

    def resolve_interview_booking_override_delta(
        self: Admission, info, *args, **kwargs
    ):
        return self.interview_booking_override_delta

    @classmethod
    @gql_has_permissions("admissions.view_admission")
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

    notes = graphene.String()

    def resolve_notes(self: Interview, info, *args, **kwargs):
        return bleach.clean(self.notes, tags=BLEACH_ALLOWED_TAGS)

    discussion = graphene.String()

    def resolve_discussion(self: Interview, info, *args, **kwargs):
        return bleach.clean(self.discussion, tags=BLEACH_ALLOWED_TAGS)

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
    current_progress = graphene.Int()
    mvp_list = graphene.List(UserNode)


class InternalGroupDiscussionData(graphene.ObjectType):
    internal_group = graphene.Field(InternalGroupNode)
    applicants_open_for_other_positions = graphene.List(ApplicantNode)
    applicant_recommendations = graphene.List(ApplicantRecommendationNode)
    applicants = graphene.List(ApplicantNode)


class CloseAdmissionData(graphene.ObjectType):
    valid_applicants = graphene.List(ApplicantNode)
    applicant_interests = graphene.List(ApplicantInterestNode)
    active_admission = graphene.Field(AdmissionNode)


class ApplicantCSVData(graphene.ObjectType):
    full_name = graphene.String()
    first_name = graphene.String()
    last_name = graphene.String()
    email = graphene.String()
    phone = graphene.String()


class ApplicantCSVDataInput(graphene.InputObjectType):
    full_name = graphene.String()
    first_name = graphene.String()
    last_name = graphene.String()
    email = graphene.String()
    phone = graphene.String()


class UploadApplicantsCSVMutation(graphene.Mutation):
    """
    Not working yet.
    """

    class Arguments:
        applicants_file = Upload(required=True)

    valid_applicants = graphene.List(ApplicantCSVData)

    @gql_has_permissions("admissions.add_applicant")
    def mutate(self, info, applicants_file, *args, **kwargs):
        applicant_data = read_admission_csv(applicants_file)
        valid_applicants = [
            ApplicantCSVData(
                full_name=applicant["name"],
                first_name=applicant["first_name"],
                last_name=applicant["last_name"],
                email=applicant["email"],
                phone=applicant["phone"],
            )
            for applicant in applicant_data
        ]
        return UploadApplicantsCSVMutation(valid_applicants=valid_applicants)


class CreateApplicantsFromCSVDataMutation(graphene.Mutation):
    """
    Not to be confused with UploadApplicantsCSVMutation. This mutation
    accepts a list of parsed data from UploadApplicantsCSVMutation and
    creates actual applicant instances
    """

    class Arguments:
        applicants = graphene.List(ApplicantCSVDataInput)

    ok = graphene.Boolean()

    @gql_has_permissions("admissions.add_applicant")
    def mutate(self, info, applicants, *args, **kwargs):
        admission = Admission.get_active_admission()
        emails = []
        for applicant in applicants:
            try:
                auth_token = token_urlsafe(32)
                applicant = Applicant.objects.create(
                    admission=admission,
                    first_name=applicant["first_name"],
                    last_name=applicant["last_name"],
                    email=applicant["email"],
                    phone=applicant["phone"],
                    token=auth_token,
                )
                ok = resend_auth_token_email(applicant)
                emails.append(applicant.email)
            except Exception as e:
                print("Failed to create applicant")
                print(e)

        return CreateApplicantsFromCSVDataMutation(ok=ok)


class ApplicantQuery(graphene.ObjectType):
    applicant = Node.Field(ApplicantNode)
    all_applicants = graphene.List(
        ApplicantNode
    )  # Can consider eliminating this endpoint?
    current_applicants = graphene.List(ApplicantNode)

    get_applicant_from_token = graphene.Field(ApplicantNode, token=graphene.String())
    internal_group_applicants_data = graphene.Field(
        InternalGroupApplicantsData, internal_group=graphene.ID()
    )
    all_internal_group_applicant_data = graphene.List(InternalGroupApplicantsData)
    internal_group_discussion_data = graphene.Field(
        InternalGroupDiscussionData,
        internal_group_id=graphene.ID(required=True),
        ordering_key=graphene.String(required=False),
    )
    all_applicants_available_for_rebooking = graphene.List(ApplicantNode)
    applicant_notices = graphene.List(ApplicantNode)
    todays_applicants = graphene.List(ApplicantNode)

    close_admission_data = graphene.Field(CloseAdmissionData)

    @gql_has_permissions("admissions.view_admission")
    def resolve_current_applicants(self, info, *args, **kwargs):
        active_admission = Admission.get_active_admission()
        return Applicant.objects.filter(admission=active_admission).order_by(
            "first_name"
        )

    @gql_has_permissions("admissions.view_admission")
    def resolve_close_admission_data(self, info, *args, **kwargs):
        # Can we do an annotation here? Kind of like unwanted = all_priorities = DO_NOT_WANT
        active_admission = Admission.get_active_admission()
        valid_applicants = (
            Applicant.objects.filter(
                admission=active_admission,
                priorities__internal_group_priority__in=[
                    InternalGroupStatus.WANT,
                    InternalGroupStatus.RESERVE,
                ],
                status=ApplicantStatus.INTERVIEW_FINISHED,
            )
            .order_by("first_name")
            .distinct()
        )

        applicant_interests = (
            ApplicantInterest.objects.filter(applicant__admission=active_admission)
            .exclude(applicant__pk__in=valid_applicants)
            .order_by("applicant__first_name")
        )

        return CloseAdmissionData(
            valid_applicants=valid_applicants,
            applicant_interests=applicant_interests,
            active_admission=active_admission,
        )

    def resolve_get_applicant_from_token(self, info, token, *args, **kwargs):
        """
        WHen this resolver is hit we can set status to 'HAS_OPENED_EMAIL probably
        """
        if token is None:
            return None

        applicant = Applicant.objects.get(token=token)
        applicant.last_activity = timezone.now()
        applicant.save()
        return applicant

    @gql_has_permissions("admissions.view_applicant")
    def resolve_all_applicants(self, info, *args, **kwargs):
        return Applicant.objects.all().order_by("first_name")

    @gql_has_permissions("admissions.view_applicant")
    def resolve_internal_group_applicants_data(
        self, info, internal_group, *args, **kwargs
    ):
        django_id = disambiguate_id(internal_group)
        internal_group = InternalGroup.objects.filter(id=django_id).first()
        if not internal_group:
            return None

        data = internal_group_applicant_data(internal_group)
        return data

    @gql_has_permissions("admissions.view_applicant")
    def resolve_all_internal_group_applicant_data(self, info, *args, **kwargs):
        admission = Admission.get_active_admission()
        if not admission:
            return None

        if admission.status != AdmissionStatus.IN_SESSION:
            return None
        positions = admission.available_internal_group_positions.all()
        internal_groups = InternalGroup.objects.filter(
            positions__in=positions
        ).distinct()

        internal_group_data = []
        for internal_group in internal_groups:
            data = internal_group_applicant_data(internal_group)
            internal_group_data.append(data)

        return internal_group_data

    @gql_has_permissions("admissions.view_applicant")
    def resolve_internal_group_discussion_data(
        self, info, internal_group_id, ordering_key="priorities", *args, **kwargs
    ):
        """
        Resolves data for the discussion view for a given internal group. This includes fields
        with all applicants having applied to this internal group, filtering of processed
        applicants and in the future other metrics like progress and remaining applicants
        to evaluate.

        """
        internal_group_id = disambiguate_id(internal_group_id)
        internal_group = InternalGroup.objects.get(pk=internal_group_id)

        active_admission = Admission.get_active_admission()
        all_applicants = Applicant.objects.filter(admission=active_admission)

        # All applicants that have applied to this internal group and finished their interview
        applicants = all_applicants.filter(
            priorities__internal_group_position__internal_group=internal_group,
            status=ApplicantStatus.INTERVIEW_FINISHED,
        ).distinct()

        if ordering_key == "interview_time":
            applicants = applicants.order_by("-interview__interview_start")
        elif ordering_key == "priorities":
            applicants = applicants.order_by(
                Case(
                    When(priorities__applicant_priority=Priority.FIRST, then=Value(2)),
                    When(priorities__applicant_priority=Priority.SECOND, then=Value(1)),
                    When(priorities__applicant_priority=Priority.THIRD, then=Value(0)),
                ),
                # I don't know why this has to be here, even when the case above is flipped
                # it still gives it in the order of Third to First priority
            ).reverse()
        else:
            raise ValueError(f"Unknown ordering key: {ordering_key}")

        # Also throw in applicants open for other positions.
        applicants_open_for_other_positions = (
            all_applicants.filter(
                open_for_other_positions=True,
                status=ApplicantStatus.INTERVIEW_FINISHED,
            )
            .exclude(pk__in=applicants)
            .distinct()
        )

        recommendations = (
            ApplicantRecommendation.objects.filter(
                internal_group=internal_group,
                applicant__status=ApplicantStatus.INTERVIEW_FINISHED,
            )
            .order_by("applicant__first_name")
            .prefetch_related("applicant__priorities", "recommended_by")
        )

        return InternalGroupDiscussionData(
            internal_group=internal_group,
            applicants_open_for_other_positions=applicants_open_for_other_positions,
            applicants=applicants,
            applicant_recommendations=recommendations,
        )

    @gql_has_permissions("admissions.view_applicant")
    def resolve_applicant_notices(self, info, *args, **kwargs):
        admission = Admission.get_active_admission()
        return Applicant.objects.filter(
            admission=admission,
            status__in=[
                ApplicantStatus.EMAIL_SENT,
                ApplicantStatus.HAS_REGISTERED_PROFILE,
            ],
        ).order_by("last_activity")

    @gql_has_permissions("admissions.view_applicant")
    def resolve_all_applicants_available_for_rebooking(self, info, *args, **kwargs):
        admission = Admission.get_active_admission()
        return Applicant.objects.filter(
            admission=admission,
            status__in=[
                ApplicantStatus.HAS_SET_PRIORITIES,
                ApplicantStatus.DID_NOT_SHOW_UP_FOR_INTERVIEW,
                ApplicantStatus.RETRACTED_APPLICATION,
                ApplicantStatus.SCHEDULED_INTERVIEW,
            ],
        ).order_by("first_name", "last_name")

    @gql_has_permissions("admissions.view_applicant")
    def resolve_todays_applicants(self, info, *args, **kwargs):
        admission = Admission.get_active_admission()
        today, today_end = midnight_timestamps_from_date(datetime.date.today())

        applicants = Applicant.objects.filter(
            admission=admission,
            status=ApplicantStatus.SCHEDULED_INTERVIEW,
            interview__interview_start__gt=today,
            interview__interview_start__lt=today_end,
        ).order_by("interview__interview_start")
        return applicants


class ResendApplicantTokenMutation(graphene.Mutation):
    class Arguments:
        email = graphene.String()

    ok = graphene.Boolean()

    def mutate(self, info, email: str, *args, **kwargs):
        active_admission = Admission.get_active_admission()
        if not active_admission or not active_admission.status == AdmissionStatus.OPEN:
            raise Exception("Admission is not open")

        email = email.strip()
        applicant = Applicant.objects.filter(email__iexact=email).first()
        if applicant:
            ok = resend_auth_token_email(applicant)
            applicant.last_activity = timezone.now()
            applicant.save()
            return ResendApplicantTokenMutation(ok=ok)
        return ResendApplicantTokenMutation(ok=False)


class CreateApplicationsMutation(graphene.Mutation):
    class Arguments:
        emails = graphene.List(graphene.String)

    ok = graphene.Boolean()
    applications_created = graphene.Int()
    faulty_emails = graphene.List(graphene.String)

    @gql_has_permissions("admissions.add_applicant")
    def mutate(self, info, emails):
        faulty_emails = []
        registered_emails = []
        for email in emails:
            try:
                applicant = Applicant.create_or_update_application(email)
                resend_auth_token_email(applicant)
                registered_emails.append(email)
            except IntegrityError:
                faulty_emails.append(email)

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

    @gql_has_permissions("admissions.view_admission")
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


class InterviewPeriodDates(graphene.ObjectType):
    start_date = graphene.Date()
    end_date = graphene.Date()


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
    default_interview_notes = graphene.NonNull(graphene.String)


class InterviewSlot(graphene.ObjectType):
    interview_start = graphene.DateTime()
    interview_ids = graphene.List(graphene.ID)


class AvailableInterviewsDayGrouping(graphene.ObjectType):
    date = graphene.Date()
    interview_slots = graphene.List(InterviewSlot)


class InterviewOverviewCell(graphene.ObjectType):

    time = graphene.String()  # Returned in HH:mm format
    content = graphene.String()  # Either "Available" or "Applicant name"
    applicant_id = (
        graphene.ID()
    )  # If content is "Applicant name", this is the applicant's ID
    interview_id = graphene.ID()
    color = graphene.String()  # Either "green" or "red"


class InterviewLocationOverviewRow(graphene.ObjectType):
    location = graphene.String()
    interviews = graphene.List(InterviewOverviewCell)


class InterviewOverviewTableData(graphene.ObjectType):
    interview_rows = graphene.List(InterviewLocationOverviewRow)
    locations = graphene.List(graphene.String)
    timestamp_header = graphene.List(graphene.String)


class UserInterviewCount(graphene.ObjectType):
    user = graphene.Field(UserNode)
    interview_count = graphene.Int()


class InterviewStatistics(graphene.ObjectType):
    total_applicants = graphene.Int()
    total_finished_interviews = graphene.Int()
    total_booked_interviews = graphene.Int()
    total_available_interviews = graphene.Int()
    user_interview_counts = graphene.List(UserInterviewCount)


class InterviewQuery(graphene.ObjectType):
    interview = Node.Field(InterviewNode)
    interview_template = graphene.Field(InterviewTemplate)
    # Intended to be used by an applicant
    interviews_available_for_booking = graphene.List(
        AvailableInterviewsDayGrouping, date_selected=graphene.Date(required=True)
    )
    interview_period_dates = graphene.Field(InterviewPeriodDates)
    # Intended to be used by an interviewer giving someone a new interview
    all_available_interviews = graphene.List(InterviewNode)
    all_future_available_interviews = graphene.List(InterviewNode)
    my_interviews = graphene.List(InterviewNode)
    my_upcoming_interviews = graphene.List(InterviewNode)
    interview_table_overview = graphene.Field(
        InterviewOverviewTableData, date=graphene.Date(required=True)
    )
    finished_interviews = graphene.List(InterviewNode)
    interview_statistics = graphene.Field(InterviewStatistics)

    @gql_has_permissions("admissions.view_interviewscheduletemplate")
    def resolve_interview_template(self, info, *args, **kwargs):
        schedule = InterviewScheduleTemplate.objects.first()

        all_boolean_evaluation_statements = (
            InterviewBooleanEvaluation.objects.all().order_by("order")
        )
        all_additional_evaluation_statements = (
            InterviewAdditionalEvaluationStatement.objects.all().order_by("order")
        )
        cleaned_default_notes = bleach.clean(
            schedule.default_interview_notes, tags=BLEACH_ALLOWED_TAGS
        )
        return InterviewTemplate(
            interview_boolean_evaluation_statements=all_boolean_evaluation_statements,
            interview_additional_evaluation_statements=all_additional_evaluation_statements,
            default_interview_notes=cleaned_default_notes,
        )

    @gql_has_permissions("admissions.view_interview")
    def resolve_my_interviews(self, info, *args, **kwargs):
        me = info.context.user
        admission = Admission.get_active_admission()
        # We already remove users from retracted applicant interviews
        # but this gives a more resilient UI
        return me.interviews_attended.filter(
            interview_start__gte=date_time_combiner(
                admission.date,
                datetime.time(hour=0, minute=0, second=0),
            )
        ).order_by("interview_start")

    @gql_has_permissions("admissions.view_interview")
    def resolve_my_upcoming_interviews(self, info, *args, **kwargs):
        me = info.context.user
        admission = Admission.get_active_admission()
        return me.interviews_attended.filter(
            applicant__admission=admission,
            applicant__isnull=False,
            interview_end__gte=timezone.now(),
        ).order_by("interview_start")

    def resolve_interview_period_dates(self, info, *args, **kwargs):
        interview_schedule_template = (
            InterviewScheduleTemplate.get_interview_schedule_template()
        )
        return InterviewPeriodDates(
            start_date=interview_schedule_template.interview_period_start_date,
            end_date=interview_schedule_template.interview_period_end_date,
        )

    def resolve_interviews_available_for_booking(
        self, info, date_selected, *args, **kwargs
    ):
        """
        The idea here is that we want to parse interviews in such a way that we only return
        a timestamp for when the interview starts, and a list of ids for interviews that
        are available for booking. This gives us a bit of security because if the interview
        is available and an applicant tries to book the same as another one they can just
        try one of the other interviews.
        """

        admission = Admission.get_active_admission()
        if (
            date_selected <= timezone.datetime.today().date()
            and not admission.interview_booking_override_enabled
        ):
            return []

        cursor = timezone.make_aware(
            timezone.datetime(
                year=date_selected.year,
                month=date_selected.month,
                day=date_selected.day,
                hour=0,
                minute=0,
                second=0,
            )
        )

        cursor_offset = cursor + timezone.timedelta(days=1)

        available_interviews_this_day = Interview.objects.filter(
            applicant__isnull=True,
            interview_start__gte=cursor,
            interview_start__lte=cursor_offset,
        )

        # At this point available interviews are all interviews within 24 hours of the date.
        # Further filtration is based on different settings
        if admission.interview_booking_override_enabled:
            # Booking override that interviews can be booked on the same day, as long as its less than
            # the override delta
            override_diff = timezone.now() + admission.interview_booking_override_delta
            available_interviews_this_day = available_interviews_this_day.filter(
                interview_start__gte=override_diff
            )

        if (
            admission.interview_booking_late_batch_enabled
            and date_selected > timezone.now().date()
        ):
            # Late batch tries to force someone to book an interview after a specific time on a given day. This is
            # typically 15:00 or 16:00. This is mostly, so they don't crash with lectures if possible
            late_batch_diff = timezone.make_aware(
                timezone.datetime(
                    year=date_selected.year,
                    month=date_selected.month,
                    day=date_selected.day,
                    hour=admission.interview_booking_late_batch_time.hour,
                    minute=admission.interview_booking_late_batch_time.minute,
                    second=admission.interview_booking_late_batch_time.second,
                )
            )
            late_batch_interviews = available_interviews_this_day.filter(
                interview_start__gte=late_batch_diff
            )
            # After filtering for late batch interviews, we want to check if there are any interviews.
            # If not we allow the applicant to book earlier in the day, meaning we do not overwrite the
            # available interviews for the day
            if late_batch_interviews.exists():
                available_interviews_this_day = late_batch_interviews

        available_interviews_timeslot_grouping = []
        parsed_interviews = create_interview_slots(
            group_interviews_by_date(available_interviews_this_day)
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

    @gql_has_permissions("admissions.view_interview")
    def resolve_all_future_available_interviews(self, info, *args, **kwargs):
        now = timezone.datetime.now()
        interviews = Interview.objects.filter(
            applicant__isnull=True, interview_start__gt=now
        )

        return interviews.order_by("-interview_start", "location__name")

    @gql_has_permissions("admissions.view_interview")
    def resolve_all_available_interviews(self, info, *args, **kwargs):
        interviews = Interview.objects.filter(
            applicant__isnull=True, interview_start__gt=timezone.now()
        )
        return interviews.order_by("interview_start", "location__name")

    @gql_has_permissions("admissions.view_interview")
    def resolve_interview_table_overview(self, info, date, *args, **kwargs):
        datetime_early, datetime_late = midnight_timestamps_from_date(date)
        interviews = Interview.objects.filter(
            interview_start__gte=datetime_early,
            interview_start__lte=datetime_late,
        )
        interview_rows, locations = interview_overview_parser(interviews)
        location_names = locations.values_list("name", flat=True)

        interview_schedule = InterviewScheduleTemplate.get_interview_schedule_template()
        default_duration = interview_schedule.default_interview_duration
        now = timezone.now()
        start = interview_schedule.default_interview_day_start

        start = timezone.datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=start.hour,
            minute=start.minute,
            second=0,
        )
        local_start = start
        end = interview_schedule.default_interview_day_end
        end = timezone.datetime(
            year=now.year,
            month=now.month,
            day=now.day,
            hour=end.hour,
            minute=end.minute,
            second=0,
        )
        local_end = end

        timestamps = []
        while local_start <= local_end:
            minute = str(local_start.minute)
            if len(minute) == 1:
                minute = "0" + minute

            hour = str(local_start.hour)
            if len(hour) == 1:
                hour = "0" + hour

            timestamp_string = hour + ":" + minute

            timestamps.append(timestamp_string)
            local_start += default_duration

        return InterviewOverviewTableData(
            interview_rows=interview_rows,
            locations=location_names,
            timestamp_header=timestamps,
        )

    @gql_has_permissions("admissions.view_interview")
    def resolve_finished_interviews(self, info, *args, **kwargs):
        return Interview.objects.filter(
            applicant__status=ApplicantStatus.INTERVIEW_FINISHED,
        ).order_by("applicant__id")

    @gql_has_permissions("admissions.view_interview")
    def resolve_interview_statistics(self, info, *args, **kwargs):
        admission = Admission.get_active_admission()
        if not admission:
            return None
        return get_interview_statistics(admission)


class InterviewLocationQuery(graphene.ObjectType):
    all_interview_locations = graphene.List(InterviewLocationNode)
    interview_overview = graphene.Field(InterviewOverviewQuery)

    @gql_has_permissions("admissions.view_interview")
    def resolve_interview_overview(self, info, *args, **kwargs):
        # We want to return all interviews in an orderly manner grouped by date and locations.
        interview_days = []
        schedule = InterviewScheduleTemplate.get_interview_schedule_template()
        date_cursor = schedule.interview_period_start_date
        interview_period_end = schedule.interview_period_end_date
        next_day = timezone.timedelta(days=1)
        start_of_day = datetime.time(hour=0, minute=0, second=0)

        # Needs to be deleted after interview period is done
        interview_pool = Interview.objects.all()

        while date_cursor <= interview_period_end:
            interview_locations = []
            # First we retrieve all interviews in a 24 hour time period
            datetime_cursor = date_time_combiner(date_cursor, start_of_day)
            interviews = interview_pool.filter(
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

        total_interviews = interview_pool.count()
        return InterviewOverviewQuery(
            interview_day_groupings=interview_days,
            interview_schedule_template=schedule,
            interview_count=total_interviews,
            admission_id=Admission.get_active_admission().id,
        )

    @gql_has_permissions("admissions.view_interview")
    def resolve_all_interview_locations(self, info, *args, **kwargs):
        return InterviewLocation.objects.all().order_by("name")


# === Applicant ===
class CreateApplicantMutation(DjangoCreateMutation):
    class Meta:
        model = Applicant
        permissions = ("admissions.add_applicant",)


class PatchApplicantMutation(DjangoPatchMutation):
    class Meta:
        model = Applicant
        # Split this into own mutation for applicant to use with token
        # permissions = ("admissions.change_applicant",)

    @classmethod
    def validate_phone_number(
        cls, root, info, value, input, id, obj: User, *args, **kwargs
    ):

        if value == "":
            raise ValidationError("Phone number cannot be empty")

        user_phone_check = User.objects.filter(phone=value).exists()
        if user_phone_check:
            raise ValidationError(
                "This phone number is already in use by another user."
            )
        applicant_phone_check = Applicant.objects.filter(phone=value).exists()
        if applicant_phone_check:
            raise ValidationError(
                "This phone number is already in use by another applicant."
            )

    @staticmethod
    def handle_image(image, name, info):
        if not image:
            return image
        file_type = image.name.split(".")[-1]
        return compress_image(image, image.name, file_type)

    @classmethod
    def after_mutate(cls, root, info, id, input, obj, return_data):
        # If applicant retracted application interviewers need to be notified
        if obj.status == ApplicantStatus.RETRACTED_APPLICATION:
            send_interview_cancelled_email(obj)
            if not hasattr(obj, "interview"):
                return obj

            interview = obj.interview
            obj.interview = None
            obj.save()

            if interview.interview_start > timezone.now():
                # Remove interviewers from interview
                notify_interviewers_cancelled_interview_email(obj, interview)
                interview.interviewers.clear()
            return obj


class ApplicantInput(graphene.InputObjectType):
    first_name = graphene.String()


class PatchApplicantByTokenMutation(graphene.Mutation):
    class Arguments:
        token = graphene.String(required=True)
        input = ApplicantInput(required=True)

    applicant = graphene.Field(ApplicantNode)

    @gql_has_permissions("admissions.change_applicant")
    def mutate(self, info, token, input):
        raise NotImplementedError("This mutation is not implemented fully yet")
        applicant = Applicant.objects.get(token=token)
        applicant = PatchApplicantMutation.mutate(
            self, info, applicant.id, input, applicant
        )
        return PatchApplicantByTokenMutation(applicant=applicant)


class DeleteApplicantMutation(DjangoDeleteMutation):
    class Meta:
        model = Applicant
        permissions = ("admissions.delete_applicant",)


class CreateApplicantCommentMutation(DjangoCreateMutation):
    class Meta:
        model = ApplicantComment
        permissions = ("admissions.add_applicantcomment",)
        auto_context_fields = {"user": "user"}
        exclude_fields = ("user",)


class SendApplicantNoticeEmailMutation(graphene.Mutation):
    class Arguments:
        applicant_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @gql_has_permissions("admissions.change_applicant")
    def mutate(self, info, applicant_id):
        applicant_id = disambiguate_id(applicant_id)
        applicant = Applicant.objects.get(id=applicant_id)
        ok = send_applicant_notice_email(applicant)
        if ok:
            applicant.notice_method = Applicant.NoticeMethod.EMAIL
            applicant.last_notice = timezone.now()
            applicant.save()
        return SendApplicantNoticeEmailMutation(ok=ok)


class ToggleApplicantWillBeAdmittedMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @gql_has_permissions("admissions.change_admission")
    def mutate(self, info, id, *args, **kwargs):
        applicant_id = disambiguate_id(id)
        applicant = Applicant.objects.get(id=applicant_id)

        applicant.will_be_admitted = not applicant.will_be_admitted
        applicant.save()
        return ToggleApplicantWillBeAdmittedMutation(success=True)


# === ApplicantInterest ===
class CreateApplicantInterestMutation(DjangoCreateMutation):
    class Meta:
        model = ApplicantInterest
        permissions = ("admissions.add_applicantinterest",)


class DeleteApplicantInterestMutation(DjangoDeleteMutation):
    class Meta:
        model = ApplicantInterest
        permissions = ("admissions.delete_applicantinterest",)


class GiveApplicantToInternalGroupMutation(graphene.Mutation):
    class Arguments:
        applicant_interest_id = graphene.ID(required=True)

    success = graphene.NonNull(graphene.Boolean)

    @gql_has_permissions("admissions.change_applicantinterest")
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


class ResetApplicantInternalGroupPositionOfferMutation(graphene.Mutation):
    class Arguments:
        applicant_interest_id = graphene.ID()

    applicant_interest = graphene.Field(ApplicantInterestNode)

    @gql_has_permissions("admissions.change_applicantinterest")
    def mutate(self, info, applicant_interest_id, *args, **kwargs):
        applicant_interest_id = disambiguate_id(applicant_interest_id)
        applicant_interest = ApplicantInterest.objects.get(pk=applicant_interest_id)
        applicant_interest.position_to_be_offered = None
        applicant_interest.save()
        return applicant_interest


# === ApplicantRecommendation ===
class CreateApplicantRecommendationMutation(DjangoCreateMutation):
    class Meta:
        model = ApplicantRecommendation
        permissions = ("admissions.add_applicantrecommendation",)
        auto_context_fields = {"recommended_by": "user"}
        exclude_fields = ("recommended_by",)


# === InternalGroupPositionPriority ===
class AddInternalGroupPositionPriorityMutation(graphene.Mutation):
    class Arguments:
        internal_group_position_id = graphene.ID(required=True)
        applicant_id = graphene.ID(required=True)

    success = graphene.Boolean()

    @gql_has_permissions("admissions.add_internalgrouppositionpriority")
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


class ApplicantAddInternalGroupPositionPriorityMutation(graphene.Mutation):
    class Arguments:
        internal_group_position_id = graphene.ID(required=True)
        token = graphene.String(required=True)

    success = graphene.Boolean()

    def mutate(self, info, internal_group_position_id, token, *args, **kwargs):
        applicant = Applicant.objects.get(token=token)
        applicant.last_activity = timezone.now()

        internal_group_position_id = disambiguate_id(internal_group_position_id)

        internal_group_position = InternalGroupPosition.objects.get(
            id=internal_group_position_id
        )

        applicant.add_priority(internal_group_position)
        return ApplicantAddInternalGroupPositionPriorityMutation(success=True)


class UpdateInternalGroupPositionPriorityOrderMutation(graphene.Mutation):
    class Arguments:
        applicant_id = graphene.ID(required=True)
        priority_order = graphene.List(graphene.ID, required=True)

    internal_group_position_priorities = graphene.List(
        InternalGroupPositionPriorityNode
    )

    @gql_has_permissions("admissions.change_internalgrouppositionpriority")
    def mutate(self, info, applicant_id, priority_order, *args, **kwargs):
        trimmed_global_ids = []
        for priority_order_id in priority_order:
            if not priority_order_id:
                continue
            trimmed_global_ids.append(priority_order_id)

        applicant_id = disambiguate_id(applicant_id)
        applicant = Applicant.objects.get(id=applicant_id)
        ids = [disambiguate_id(global_id) for global_id in trimmed_global_ids]

        parsed_priorities = []
        for id in ids:
            parsed_priorities.append(InternalGroupPosition.objects.get(id=id))

        applicant.update_priority_order(parsed_priorities)
        applicant.refresh_from_db()
        new_priorities = applicant.get_priorities
        return UpdateInternalGroupPositionPriorityOrderMutation(
            internal_group_position_priorities=new_priorities
        )


class ApplicantUpdateInternalGroupPositionPriorityOrderMutation(graphene.Mutation):
    """
    Graphql endpoint allowing an applicant to change their priority order, given
    that they provide a token.
    """

    class Arguments:
        priority_order = graphene.List(graphene.ID, required=True)
        token = graphene.String(required=True)

    internal_group_position_priorities = graphene.List(
        InternalGroupPositionPriorityNode
    )

    def mutate(self, info, priority_order, token, *args, **kwargs):
        admission = Admission.get_active_admission()
        if not admission or not admission.status == AdmissionStatus.OPEN:
            raise Exception("Admission is in session or not open")

        applicant = Applicant.objects.get(token=token)
        applicant.last_activity = timezone.now()
        constructed_priorities = construct_new_priority_list(priority_order)
        applicant.update_priority_order(constructed_priorities)
        applicant.refresh_from_db()
        new_priorities = applicant.get_priorities
        return ApplicantUpdateInternalGroupPositionPriorityOrderMutation(
            internal_group_position_priorities=new_priorities
        )


class PatchInternalGroupPositionPriority(DjangoPatchMutation):
    class Meta:
        model = InternalGroupPositionPriority
        permissions = ("admissions.change_internalgrouppositionpriority",)


class DeleteInternalGroupPositionPriority(DjangoDeleteMutation):
    class Meta:
        model = InternalGroupPositionPriority
        permissions = ("admissions.delete_internalgrouppositionpriority",)

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


class ApplicantDeleteInternalGroupPositionPriority(graphene.Mutation):
    class Arguments:
        internal_group_position_id = graphene.ID(required=True)
        token = graphene.String(required=True)

    success = graphene.Boolean()

    def mutate(self, info, internal_group_position_id, token, *args, **kwargs):
        applicant = Applicant.objects.get(token=token)
        internal_group_position_id = disambiguate_id(internal_group_position_id)
        internal_group_position = InternalGroupPosition.objects.get(
            id=internal_group_position_id
        )

        # move this to a model method
        remove_applicant_choice(applicant, internal_group_position)
        return ApplicantDeleteInternalGroupPositionPriority(success=True)


# === Admission ===
class CreateAdmissionMutation(DjangoCreateMutation):
    class Meta:
        model = Admission
        permissions = ("admissions.add_admission",)


class PatchAdmissionMutation(DjangoPatchMutation):
    class Meta:
        model = Admission
        permissions = ("admissions.change_admission",)


class DeleteAdmissionMutation(DjangoDeleteMutation):
    class Meta:
        model = Admission
        permissions = ("admissions.delete_admission",)


class LockAdmissionMutation(graphene.Mutation):
    # Final stage before we decide who is admitted into KSG.
    # Requires that all applicants have been evaluated in som manner
    admission = graphene.Field(AdmissionNode)

    @gql_has_permissions("admissions.change_admission")
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

    @gql_has_permissions("admissions.change_admission")
    def mutate(self, info, *args, **kwargs):
        """
        1. Get all applicants we have marked for admission or with and
           offer from an internal group
        2. Create a user instance for all of them with their data
        3. Give them the internal group position they were admitted for
        4. obfuscate identifying applicant information
        5. Delete all applicant comments and interviews
        6. Close the admission
        """
        # Step 1)
        admission = Admission.get_active_admission()
        admitted_applicants = get_admission_final_applicant_qs(admission)
        failed_user_generation = []
        with transaction.atomic():
            # Would rather trigger an error and not finish the transaction
            # if something went wrong
            for applicant in admitted_applicants:
                # Step 2)
                applicant_user_profile = User.objects.create(
                    # Most probable where error will happen on
                    # too long values or unique constraint
                    username=applicant.email,
                    first_name=applicant.first_name,
                    last_name=applicant.last_name,
                    email=applicant.email,
                    profile_image=applicant.image,
                    phone=applicant.phone,
                    start_ksg=datetime.datetime.today(),
                    study_address=applicant.address,
                    home_town=applicant.hometown,
                    study=applicant.study,
                    date_of_birth=applicant.date_of_birth,
                    admission=admission,
                )

                # Step 3)
                # We give the applicant the internal group position they have been accepted into
                internal_group_position = get_applicant_offered_position(applicant)

                # Need to establish the membership type which we infer from the position data.
                # Should be unique for each admission + position. Raises Exception otherwise
                membership_type = (
                    AdmissionAvailableInternalGroupPositionData.objects.get(
                        admission=admission,
                        internal_group_position=internal_group_position,
                    ).membership_type
                )
                InternalGroupPositionMembership.objects.create(
                    position=internal_group_position,
                    user=applicant_user_profile,
                    date_joined=datetime.date.today(),
                    type=membership_type,
                )

                SociBankAccount.objects.create(
                    user=applicant_user_profile, balance=0, card_uuid=None
                )

        # Step 4)
        # User generation is done. Now we want to remove all identifying information
        # As of now "05-07-2023" this doesn't really do anything since we nuke everything
        obfuscate_admission(admission)

        # Step 5)
        # Delete all applicant related data
        ApplicantComment.objects.all().delete()
        Interview.objects.all().delete()
        ApplicantRecommendation.objects.all().delete()
        ApplicantInterest.objects.all().delete()

        # Step 6)
        # It's a wrap folks
        admission.status = AdmissionStatus.CLOSED
        admission.closed_at = timezone.now()
        admission.save()
        admitted_applicants.update(will_be_admitted=False)
        return CloseAdmissionMutation(failed_user_generation=failed_user_generation)


# === Interview ===
class GenerateInterviewsMutation(graphene.Mutation):
    ok = graphene.Boolean()
    interviews_generated = graphene.Int()

    @gql_has_permissions("admissions.add_interview")
    def mutate(self, info, *args, **kwargs):
        # retrieve the schedule template
        schedule = InterviewScheduleTemplate.objects.all().first()
        # should handle this a bit better probably
        generate_interviews_from_schedule(schedule)
        num = Interview.objects.all().count()
        return GenerateInterviewsMutation(ok=True, interviews_generated=num)


class CreateInterviewMutation(DjangoCreateMutation):
    class Meta:
        model = Interview
        permissions = ("admissions.add_interview",)
        exclude_fields = ("additional_evaluations", "boolean_evaluations")

    @classmethod
    def after_mutate(cls, root, info, input, obj, return_data):
        from .utils import add_evaluations_to_interview

        add_evaluations_to_interview(obj)
        return return_data


class DeleteInterviewMutation(DjangoDeleteMutation):
    class Meta:
        model = Interview
        permissions = ("admissions.delete_interview",)

    @classmethod
    def before_save(cls, root, info, id, obj):
        if obj.get_applicant:
            raise Exception("Interview is not empty")

        return obj


class SetSelfAsInterviewerMutation(graphene.Mutation):
    class Arguments:
        interview_id = graphene.ID(required=True)

    success = graphene.Boolean()

    def mutate(self, info, interview_id, *args, **kwargs):
        interview_django_id = disambiguate_id(interview_id)
        interview = Interview.objects.get(pk=interview_django_id)

        now = timezone.now()
        user = info.context.user
        if interview.interview_end < now:
            raise Exception(f"Cannot assign {user} to interview that is over")

        if user.interviews_attended.filter(
            interview_start=interview.interview_start, applicant__isnull=False
        ).exists():
            raise Exception(f"{user} is already attending an interview at this time")

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
        permissions = ("admissions.change_interview",)
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

    @gql_has_permissions("admissions.delete_interview")
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
        applicant.last_activity = timezone.now()

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
                send_interview_confirmation_email(interview)
                return BookInterviewMutation(ok=True)

            except IntegrityError:  # Someone already booked this interview
                pass
            except Interview.DoesNotExist:
                pass

        return BookInterviewMutation(ok=False)


class AssignApplicantNewInterviewMutation(graphene.Mutation):
    class Arguments:
        applicant_id = graphene.ID(required=True)
        interview_id = graphene.ID(required=True)

    success = graphene.Boolean()

    @gql_has_permissions("admissions.change_applicant")
    def mutate(self, info, applicant_id, interview_id, *args, **kwargs):
        applicant_id = disambiguate_id(applicant_id)
        interview_id = disambiguate_id(interview_id)
        applicant = Applicant.objects.get(pk=applicant_id)
        interview = Interview.objects.get(pk=interview_id)

        if hasattr(interview, "applicant"):
            raise Exception(
                f"Interview already has an applicant assigned: {interview.applicant}"
            )

        with transaction.atomic():
            existing_interview = applicant.interview
            if existing_interview:
                existing_interview.applicant = None
                existing_interview.save()

            interview.applicant = applicant
            interview.save()
            applicant.status = ApplicantStatus.SCHEDULED_INTERVIEW
            applicant.save()

            send_new_interview_mail(applicant)
            # TODO send email to interviewers

            return AssignApplicantNewInterviewMutation(success=True)


class RemoveApplicantFromInterviewMutation(graphene.Mutation):
    class Arguments:
        interview_id = graphene.ID(required=True)

    interview = graphene.Field(InterviewNode)

    @gql_has_permissions("admissions.change_interview")
    def mutate(self, info, interview_id, *args, **kwargs):
        interview_id = disambiguate_id(interview_id)
        interview = Interview.objects.get(pk=interview_id)
        applicant = interview.get_applicant

        now = timezone.now()

        if interview.interview_start < now:
            raise Exception("Cannot remove applicant from interview in the past")

        if not applicant:
            raise Exception("Interview is not booked")

        if applicant.status == ApplicantStatus.INTERVIEW_FINISHED:
            raise Exception("Applicant has already finished the interview")

        with transaction.atomic():
            interview.applicant = None
            interview.save()
            applicant.status = ApplicantStatus.HAS_SET_PRIORITIES
            applicant.save()
            notify_interviewers_applicant_has_been_removed_from_interview_email(
                applicant, interview
            )

        return RemoveApplicantFromInterviewMutation(interview=interview)


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
    patch_appicant_by_token = PatchApplicantByTokenMutation.Field()
    delete_applicant = DeleteApplicantMutation.Field()
    upload_applicants_csv = UploadApplicantsCSVMutation.Field()
    create_applicants_from_csv_data = CreateApplicantsFromCSVDataMutation.Field()
    update_internal_group_position_priority_order = (
        UpdateInternalGroupPositionPriorityOrderMutation.Field()
    )
    applicant_update_internal_group_position_priority_order = (
        ApplicantUpdateInternalGroupPositionPriorityOrderMutation.Field()
    )
    send_applicant_notice = SendApplicantNoticeEmailMutation.Field()

    create_applicant_comment = CreateApplicantCommentMutation.Field()
    create_applicant_recommendation = CreateApplicantRecommendationMutation.Field()

    create_applicant_interest = CreateApplicantInterestMutation.Field()
    delete_applicant_interest = DeleteApplicantInterestMutation.Field()

    give_applicant_to_internal_group = GiveApplicantToInternalGroupMutation.Field()
    reset_applicant_internal_group_position_offer = (
        ResetApplicantInternalGroupPositionOfferMutation.Field()
    )

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
    create_interview = CreateInterviewMutation.Field()
    delete_interview = DeleteInterviewMutation.Field()
    book_interview = BookInterviewMutation.Field()
    assign_applicant_new_interview = AssignApplicantNewInterviewMutation.Field()
    remove_applicant_from_interview = RemoveApplicantFromInterviewMutation.Field()
    delete_all_interviews = DeleteAllInterviewsMutation.Field()
    set_self_as_interviewer = SetSelfAsInterviewerMutation.Field()
    remove_self_as_interviewer = RemoveSelfAsInterviewerMutation.Field()
    toggle_applicant_will_be_admitted = ToggleApplicantWillBeAdmittedMutation.Field()
    lock_admission = LockAdmissionMutation.Field()
    close_admission = CloseAdmissionMutation.Field()

    add_internal_group_position_priority = (
        AddInternalGroupPositionPriorityMutation.Field()
    )
    applicant_add_internal_group_position_priority = (
        ApplicantAddInternalGroupPositionPriorityMutation.Field()
    )
    patch_internal_group_position_priority = PatchInternalGroupPositionPriority.Field()
    delete_internal_group_position_priority = (
        DeleteInternalGroupPositionPriority.Field()
    )
    applicant_delete_internal_group_position_priority = (
        ApplicantDeleteInternalGroupPositionPriority.Field()
    )
