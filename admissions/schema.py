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

    def resolve_internal_group_priority(self, info, *args, **kwargs):
        # Shady. Should do something else about this
        if self.internal_group_priority == "":
            return None
        return self.internal_group_priority


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
    priorities = graphene.List(InternalGroupPositionPriorityNode)

    interviewer_from_internal_group = graphene.ID(internal_group_id=graphene.ID())

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
        ).first()  # Should only be one

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


class BooleanEvaluationAnswer(graphene.ObjectType):
    statement = graphene.String()
    answer = graphene.Boolean()


class InterviewNode(DjangoObjectType):
    class Meta:
        model = Interview
        interfaces = (Node,)

    interviewers = graphene.List(UserNode)
    boolean_evaluation_answers = graphene.List(BooleanEvaluationAnswer)

    def resolve_boolean_evaluation_answers(self: Interview, info, *args, **kwargs):
        evaluations = []
        for evaluation in self.boolean_evaluation_answers.all().order_by(
            "statement__order"
        ):
            evaluations.append(
                BooleanEvaluationAnswer(
                    statement=evaluation.statement.statement, answer=evaluation.value
                )
            )
        return evaluations

    def resolve_interviewers(self: Interview, info, *args, **kwargs):
        return self.interviewers.all()

    @classmethod
    def get_node(cls, info, id):
        return Interview.objects.get(pk=id)


class InternalGroupApplicantsData(graphene.ObjectType):
    """
    A way to encapsulate the applicants for a given internal group
        > Resolves all applicants for this group split into their priorities
    """

    internal_group_name = graphene.String()
    first_priorities = graphene.List(ApplicantNode)
    second_priorities = graphene.List(ApplicantNode)
    third_priorities = graphene.List(ApplicantNode)


class ApplicantQuery(graphene.ObjectType):
    applicant = Node.Field(ApplicantNode)
    all_applicants = graphene.List(ApplicantNode)
    get_applicant_from_token = graphene.Field(ApplicantNode, token=graphene.String())
    internal_group_applicants_data = graphene.Field(
        InternalGroupApplicantsData, internal_group=graphene.ID()
    )

    valid_applicants = graphene.List(ApplicantNode)

    def resolve_valid_applicants(self, info, *args, **kwargs):
        applicants = Applicant.objects.filter(
            ~Q(priorities__internal_group_priority=InternalGroupStatus.DO_NOT_WANT),
            status=ApplicantStatus.INTERVIEW_FINISHED,
        ).order_by("first_name")
        return applicants

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

        first_priorities = (
            Applicant.objects.all()
            .filter(
                priorities__applicant_priority=Priority.FIRST,
                priorities__internal_group_position__internal_group=internal_group,
            )
            .order_by("interview__interview_start")
        )
        second_priorities = (
            Applicant.objects.all()
            .filter(
                priorities__applicant_priority=Priority.SECOND,
                priorities__internal_group_position__internal_group=internal_group,
            )
            .order_by("interview__interview_start")
        )
        third_priorities = (
            Applicant.objects.all()
            .filter(
                priorities__applicant_priority=Priority.THIRD,
                priorities__internal_group_position__internal_group=internal_group,
            )
            .order_by("interview__interview_start")
        )
        return InternalGroupApplicantsData(
            internal_group_name=internal_group.name,
            first_priorities=first_priorities,
            second_priorities=second_priorities,
            third_priorities=third_priorities,
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


class CloseAdmissionMutation(graphene.Mutation):
    failed_user_generation = graphene.List(ApplicantNode)

    def mutate(self, info, *args, **kwargs):
        """
        1. Get all applicants we have marked for admission
        2. Create a user instance for all of them with their data
        3. Should be able to handle some shitty inputs
        4. Give them the internal group position they were admitted for
        5. obfuscate admission
        6. Close the admission
        """
        admission = Admission.get_active_admission()
        admitted_applicants = Applicant.objects.filter(
            will_be_admitted=True, admission=admission
        )
        failed_user_generation = []
        for applicant in admitted_applicants:
            try:
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
                Unique constraints that can be fucked up here
                1. How should we handle emails? Do this at applicant stage?
                2. 
                """
                # We give the applicant the internal group position they have been accepted into
                priorities = applicant.get_priorities
                for priority in priorities:
                    # We find the first priority from the applicant where the internal group has marked
                    # it as "WANT"
                    if priority is None:
                        continue
                    if priority.internal_group_priority != InternalGroupStatus.WANT:
                        continue

                    internal_group_position = priority.internal_group_position
                    InternalGroupPositionMembership.objects.create(
                        position=internal_group_position,
                        user=applicant_user_profile,
                        date_joined=datetime.date.today(),
                    )
                    # We found their assigned position, eject.
                    break
                SociBankAccount.objects.create(
                    user=applicant_user_profile, balance=0, card_uuid=None
                )

            except Exception as e:
                failed_user_generation.append(applicant)

        # User generation is done. Now we want to remove all identifying information
        obfuscate_admission(admission)

        # It's a wrap folks
        admission.status = AdmissionStatus.CLOSED
        admission.save()
        admitted_applicants.update(will_be_admitted=False)

        return CloseAdmissionMutation(failed_user_generation=failed_user_generation)


# This can probably be deleted
class ObfuscateAdmissionMutation(graphene.Mutation):
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
    obfuscate_admission = ObfuscateAdmissionMutation.Field()
    delete_all_interviews = DeleteAllInterviewsMutation.Field()
    set_self_as_interviewer = SetSelfAsInterviewerMutation.Field()
    remove_self_as_interviewer = RemoveSelfAsInterviewerMutation.Field()
    toggle_applicant_will_be_admitted = ToggleApplicantWillBeAdmittedMutation.Field()
    close_admission = CloseAdmissionMutation.Field()

    add_internal_group_position_priority = (
        AddInternalGroupPositionPriorityMutation.Field()
    )
    delete_internal_group_position_priority = (
        DeleteInternalGroupPositionPriority.Field()
    )
