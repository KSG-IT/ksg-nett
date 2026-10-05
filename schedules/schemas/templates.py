import datetime

import graphene
from django.db.models import Case, When, Value
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)

from common.decorators import gql_has_permissions
from schedules.models import ScheduleTemplate, ShiftTemplate, ShiftSlotTemplate
from graphene_django_cud.util import disambiguate_id

from schedules.permissions import (
    ManagedCreateMixin,
    ManagedDeleteMixin,
    ManagedPatchMixin,
    require_can_manage_schedule,
)
from schedules.utils.templates import replace_impact


class ShiftSlotTemplateNode(DjangoObjectType):
    class Meta:
        model = ShiftSlotTemplate
        interfaces = (Node,)


class ShiftTemplateNode(DjangoObjectType):
    class Meta:
        model = ShiftTemplate
        interfaces = (Node,)

    duration = graphene.String()
    shift_slot_templates = graphene.List(ShiftSlotTemplateNode)

    def resolve_duration(self: ShiftTemplate, info):
        from schedules.utils.templates import shift_template_timestamps_to_datetime

        datetime_start, datetime_end = shift_template_timestamps_to_datetime(
            datetime.date.today(), self
        )
        return datetime_end - datetime_start

    def resolve_shift_slot_templates(self: ShiftTemplate, info):
        return self.shift_slot_templates.all()

    @classmethod
    @gql_has_permissions("schedules.view_shifttemplate")
    def get_node(cls, info, id):
        return ShiftTemplate.objects.get(pk=id)


class ScheduleTemplateNode(DjangoObjectType):
    class Meta:
        model = ScheduleTemplate
        interfaces = (Node,)

    shift_templates = graphene.List(ShiftTemplateNode)

    def resolve_shift_templates(self: ScheduleTemplate, info, *args, **kwargs):
        # Transform each day to a numerical value so we can sort by it
        return self.shift_templates.all().order_by(
            Case(
                When(day=ShiftTemplate.Day.MONDAY, then=Value(0)),
                When(day=ShiftTemplate.Day.TUESDAY, then=Value(1)),
                When(day=ShiftTemplate.Day.WEDNESDAY, then=Value(2)),
                When(day=ShiftTemplate.Day.THURSDAY, then=Value(3)),
                When(day=ShiftTemplate.Day.FRIDAY, then=Value(4)),
                When(day=ShiftTemplate.Day.SATURDAY, then=Value(5)),
                When(day=ShiftTemplate.Day.SUNDAY, then=Value(6)),
            ),
            "location",
            "time_start",
        )

    @classmethod
    @gql_has_permissions("schedules.view_scheduletemplate")
    def get_node(cls, info, id):
        return ScheduleTemplate.objects.get(pk=id)


class TemplateGenerationPreviewNode(graphene.ObjectType):
    first_day = graphene.NonNull(graphene.Date)
    last_day = graphene.NonNull(graphene.Date)
    shifts_to_create = graphene.NonNull(graphene.Int)
    shifts_to_delete = graphene.NonNull(graphene.Int)
    filled_slots_to_delete = graphene.NonNull(graphene.Int)
    answers_to_delete = graphene.NonNull(graphene.Int)
    drafts_to_delete = graphene.NonNull(graphene.Int)
    needs_confirmation = graphene.NonNull(
        graphene.Boolean,
        description="True when generateShiftsFromTemplate needs confirmDelete",
    )


class ScheduleTemplateQuery(graphene.ObjectType):
    schedule_template = Node.Field(ScheduleTemplateNode)
    all_schedule_templates = graphene.List(ScheduleTemplateNode)
    template_generation_preview = graphene.Field(
        graphene.NonNull(TemplateGenerationPreviewNode),
        schedule_template_id=graphene.ID(required=True),
        start_date=graphene.Date(required=True),
        number_of_weeks=graphene.Int(required=True),
        description="What generateShiftsFromTemplate would make and delete",
    )

    @gql_has_permissions("schedules.add_shift")
    def resolve_template_generation_preview(
        self, info, schedule_template_id, start_date, number_of_weeks
    ):
        template = ScheduleTemplate.objects.get(
            pk=disambiguate_id(schedule_template_id)
        )
        require_can_manage_schedule(
            info.context.user, template.schedule, "schedules.add_shift"
        )
        return replace_impact(template, start_date, number_of_weeks)

    @gql_has_permissions("schedules.view_scheduletemplate")
    def resolve_all_schedule_templates(self, info, *args, **kwargs):
        return ScheduleTemplate.objects.all().order_by("schedule__name")


class CreateScheduleTemplateMutation(ManagedCreateMixin, DjangoCreateMutation):
    class Meta:
        model = ScheduleTemplate
        permissions = ("schedules.add_scheduletemplate",)


class DeleteScheduleTemplateMutation(ManagedDeleteMixin, DjangoDeleteMutation):
    class Meta:
        model = ScheduleTemplate
        permissions = ("schedules.delete_scheduletemplate",)


class CreateShiftSlotTemplateMutation(ManagedCreateMixin, DjangoCreateMutation):
    class Meta:
        model = ShiftSlotTemplate
        permissions = ("schedules.add_shiftslottemplate",)


class PatchShiftSlotTemplateMutation(ManagedPatchMixin, DjangoPatchMutation):
    class Meta:
        model = ShiftSlotTemplate
        permissions = ("schedules.change_shiftslottemplate",)


class DeleteShiftSlotTemplateMutation(ManagedDeleteMixin, DjangoDeleteMutation):
    class Meta:
        model = ShiftSlotTemplate
        permissions = ("schedules.delete_shiftslottemplate",)


class CreateShiftTemplateMutation(ManagedCreateMixin, DjangoCreateMutation):
    class Meta:
        model = ShiftTemplate
        permissions = ("schedules.add_shifttemplate",)


class DeleteShiftTemplateMutation(ManagedDeleteMixin, DjangoDeleteMutation):
    class Meta:
        model = ShiftTemplate
        permissions = ("schedules.delete_shifttemplate",)


class ScheduleTemplateMutations(graphene.ObjectType):
    create_schedule_template = CreateScheduleTemplateMutation.Field()
    delete_schedule_template = DeleteScheduleTemplateMutation.Field()

    create_shift_slot_template = CreateShiftSlotTemplateMutation.Field()
    patch_shift_slot_template = PatchShiftSlotTemplateMutation.Field()
    delete_shift_slot_template = DeleteShiftSlotTemplateMutation.Field()

    create_shift_template = CreateShiftTemplateMutation.Field()
    delete_shift_template = DeleteShiftTemplateMutation.Field()
