import graphene
from graphene import Node
from graphene_django import DjangoObjectType
from django.db import IntegrityError
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from graphene_django.filter import DjangoFilterConnectionField
from common.util import send_email
from admissions.utils import generate_interviews_from_schedule
from admissions.models import (
    Applicant,
    Admission,
    AdmissionAvailableInternalGroupPositionData,
    InterviewAdditionalEvaluationStatement,
    InternalGroupPositionPriority,
    InterviewBooleanEvaluationAnswer,
    InterviewAdditionalEvaluationAnswer,
    Interview,
    InterviewBooleanEvaluation,
    InterviewScheduleTemplate,
    ApplicantUnavailability,
)
from admissions.filters import AdmissionFilter, ApplicantFilter
from organization.models import InternalGroup


class InternalGroupPositionPriorityNode(DjangoObjectType):
    class Meta:
        model = InternalGroupPositionPriority
        interfaces = (Node,)


class ApplicantNode(DjangoObjectType):
    class Meta:
        model = Applicant
        interfaces = (Node,)

    full_name = graphene.String(source="get_full_name")

    first_choice = graphene.Field(InternalGroupPositionPriorityNode)
    second_choice = graphene.Field(InternalGroupPositionPriorityNode)
    third_choice = graphene.Field(InternalGroupPositionPriorityNode)

    def resolve_first_choice(self: Applicant, info, *args, **kwargs):
        return self.objects.filter(priority="first").first()

    def resolve_second_choice(self: Applicant, info, *args, **kwargs):
        return self.objects.filter(priority="second").first()

    def resolve_third_choice(self: Applicant, info, *args, **kwargs):
        return self.objects.filter(priority="third").first()

    @classmethod
    def get_node(cls, info, id):
        return Applicant.objects.get(pk=id)


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
    available_internal_group_positions = graphene.NonNull(
        graphene.List(AdmissionAvailableInternalGroupPositionDataNode)
    )
    applicants = graphene.List(ApplicantNode)

    def resolve_applicants(self: Admission, info, *args, **kwargs):
        return self.applicants.all().order_by("first_name")

    def resolve_available_internal_group_positions(
        self: Admission, info, *args, **kwargs
    ):
        return self.available_internal_group_positions.all()

    @classmethod
    def get_node(cls, info, id):
        return Admission.objects.get(pk=id)


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
            content = _(
                """
                Hei og velkommen til KSG sin søkerportal! 

                Trykk på denne linken for å registrere søknaden videre, eller se intervjutiden din.

                Lenke: %(link)s
                """
            ) % {
                "link": f"{settings.APP_URL}/applicant-portal/{applicant.token}",
            }

            html_content = _(
                """
                Hei og velkommen til KSG sin søkerportal! 
                <br />
                Trykk på denne linken for å registrere søknaden videre, eller se intervjutiden din.
                <br />
                <a href="%(link)s">Registrer søknad</a><br />
                <br />
                """
            ) % {
                "link": f"{settings.APP_URL}/applicant-portal/{applicant.token}",
            }

            return send_email(
                _("KSG søkerportal"),
                message=content,
                html_message=html_content,
                recipients=[applicant.email],
            )
        return ResendApplicantTokenMutation(ok=True)


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

    def resolve_active_admission(self, info, *args, **kwargs):
        admission = Admission.objects.filter(status="open")
        if len(admission) > 1:
            raise Admission.MultipleObjectsReturned

        if not admission:
            return None

        return admission.first()

    def resolve_all_admissions(self, info, *args, **kwargs):
        return Admission.objects.all().order_by("-date")


class CreateApplicantMutation(DjangoCreateMutation):
    class Meta:
        model = Applicant


class PatchApplicantMutation(DjangoPatchMutation):
    class Meta:
        model = Applicant


class DeleteApplicantMutation(DjangoDeleteMutation):
    class Meta:
        model = Applicant


class CreateAdmissionMutation(DjangoCreateMutation):
    class Meta:
        model = Admission


class PatchAdmissionMutation(DjangoPatchMutation):
    class Meta:
        model = Admission


class DeleteAdmissionMutation(DjangoDeleteMutation):
    class Meta:
        model = Admission


class GenerateInterviewScheduleMutation(graphene.Mutation):
    class Arguments:
        pass

    ok = graphene.Boolean()
    interviews_generated = graphene.Int()

    def mutate(self, info, *args, **kwargs):
        # retrieve the schedule template
        schedule = (
            InterviewScheduleTemplate.objects.all().first()
        )  # should handle this a bit better probably
        generate_interviews_from_schedule(schedule)
        num = Interview.objects.all().count()

        return GenerateInterviewScheduleMutation(ok=True, interviews_generated=num)


class AdmissionsMutations(graphene.ObjectType):
    create_applicant = CreateApplicantMutation.Field()
    patch_applicant = PatchApplicantMutation.Field()
    delete_applicant = DeleteApplicantMutation.Field()

    create_applications = CreateApplicationsMutation.Field()

    create_admission = CreateAdmissionMutation.Field()
    patch_admission = PatchAdmissionMutation.Field()
    delete_admission = DeleteAdmissionMutation.Field()

    re_send_application_token = ResendApplicantTokenMutation.Field()
    generate_interviews_from_schedule = GenerateInterviewScheduleMutation.Field()
