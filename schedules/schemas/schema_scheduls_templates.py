import graphene
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django import DjangoConnectionField
from schedules.models import (
    ScheduleTemplate,
    ShiftSlotTemplate,
    ShiftSlotGroupTemplate,
)


class ScheduleTemplateNode(DjangoObjectType):
    class Meta:
        model = ScheduleTemplate
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return ScheduleTemplate.objects.get(pk=id)


class ShiftSlotTemplateNode(DjangoObjectType):
    class Meta:
        model = ShiftSlotTemplate
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return ShiftSlotTemplate.objects.get(pk=id)


class ShiftSlotGroupTemplateNode(DjangoObjectType):
    class Meta:
        model = ShiftSlotGroupTemplate
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return ShiftSlotGroupTemplate.objects.get(pk=id)


# QUERIES


class ScheduleTemplateQuery(graphene.ObjectType):
    schedule_template = Node.Field(ScheduleTemplateNode)
    all_schedule_template = DjangoConnectionField(ScheduleTemplateNode)

    def resolve_all_schedule_templates(self, info, *args, **kwargs):
        return ScheduleTemplate.objects.all().order_by("name")


class ShiftSlotTemplateQuery(graphene.ObjectType):
    shift_slot_template = Node.Field(ShiftSlotTemplateNode)
    all_shift_slot_templates = DjangoConnectionField(ShiftSlotTemplateNode)

    def resolve_all_shift_slot_templates(self, info, *args, **kwargs):
        return ShiftSlotTemplate.objects.all()


class ShiftSlotGroupTemplateQuery(graphene.ObjectType):
    shift_slot_group_template = Node.Field(ShiftSlotGroupTemplateNode)
    all_shift_slot_group_templates = DjangoConnectionField(ShiftSlotGroupTemplateNode)

    def resolve_shift_slot_group_templates(self, info, *args, **kwargs):
        return ShiftSlotGroupTemplate.objects.all()


# MUTATIONS


class CreateScheduleTemplateMutation(DjangoCreateMutation):
    class Meta:
        model = ScheduleTemplate


class PatchScheduleTemplateMutation(DjangoPatchMutation):
    class Meta:
        model = ScheduleTemplate


class DeleteScheduleTemplateMutation(DjangoDeleteMutation):
    class Meta:
        model = ScheduleTemplate


class CreateShiftSlotTemplateMutation(DjangoCreateMutation):
    class Meta:
        model = ShiftSlotTemplate


class PatchShiftSlotTemplateMutation(DjangoPatchMutation):
    class Meta:
        model = ShiftSlotTemplate


class DeleteShiftSlotTemplateMutation(DjangoDeleteMutation):
    class Meta:
        model = ShiftSlotTemplate


class CreateShiftSlotGroupTemplateMutation(DjangoCreateMutation):
    class Meta:
        model = ShiftSlotGroupTemplate


class PatchShiftSlotGroupTemplateMutation(DjangoPatchMutation):
    class Meta:
        model = ShiftSlotGroupTemplate


class DeleteShiftSlotGroupTemplateMutation(DjangoDeleteMutation):
    class Meta:
        model = ShiftSlotGroupTemplate


class SchedulesTemplateMutations(graphene.ObjectType):
    create_schedule_template = CreateScheduleTemplateMutation.Field()
    patch_schedule_template = PatchScheduleTemplateMutation.Field()
    delete_schedule_template = DeleteScheduleTemplateMutation.Field()

    create_shift_slot_template = CreateShiftSlotTemplateMutation.Field()
    patch_shift_slot_template = PatchShiftSlotTemplateMutation.Field()
    delete_shift_slot_template = DeleteShiftSlotTemplateMutation.Field()

    create_shift_slot_group_template = CreateShiftSlotGroupTemplateMutation.Field()
    patch_shift_slot_group_template = PatchShiftSlotGroupTemplateMutation.Field()
    delete_shift_slot_group_template = DeleteShiftSlotGroupTemplateMutation.Field()
