import graphene
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django.filter import DjangoFilterConnectionField

from admissions.models import (
    Applicant,
    Admission,
)
from admissions.filters import AdmissionFilter, ApplicantFilter


class ApplicantNode(DjangoObjectType):
    class Meta:
        model = Applicant
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return Applicant.objects.get(pk=id)


class AdmissionNode(DjangoObjectType):
    class Meta:
        model = Admission
        interfaces = (Node,)

    semester = graphene.String(source="semester")

    @classmethod
    def get_node(cls, info, id):
        return Admission.objects.get(pk=id)


class ApplicantQuery(graphene.ObjectType):
    applicant = Node.Field(ApplicantNode)
    all_applicants = DjangoFilterConnectionField(
        ApplicantNode, filterset_class=ApplicantFilter
    )

    def resolve_all_applicants(self, info, *args, **kwargs):
        return Applicant.objects.all().order_by("first_name")


class AdmissionQuery(graphene.ObjectType):
    admission = Node.Field(AdmissionNode)
    all_admissions = DjangoFilterConnectionField(
        AdmissionNode, filterset_class=AdmissionFilter
    )

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


class AdmissionsMutations(graphene.ObjectType):
    create_applicant = CreateApplicantMutation.Field()
    patch_applicant = PatchApplicantMutation.Field()
    delete_applicant = DeleteApplicantMutation.Field()

    create_admission = CreateAdmissionMutation.Field()
    patch_admission = PatchAdmissionMutation.Field()
    delete_admission = DeleteAdmissionMutation.Field()
