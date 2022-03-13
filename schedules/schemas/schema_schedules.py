# This schedule deals with all models pertaining to actual shift management and nothing
# automated through templates

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
    Schedule,
    ScheduleSlotType,
    Shift,
    ShiftSlot,
    ShiftTrade,
    ShiftSlotGroup,
    ShiftSlotGroupInterest,
    ShiftTradeOffer,
    ShiftSlotGroupDayRule,
)


class ScheduleNode(DjangoObjectType):
    class Meta:
        model = Schedule
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return Schedule.objects.get(pk=id)


class ScheduleSlotTypeNode(DjangoObjectType):
    class Meta:
        model = ScheduleSlotType
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return ScheduleSlotType.objects.get(pk=id)


class ShiftNode(DjangoObjectType):
    class Meta:
        model = Shift
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return Shift.objects.get(pk=id)


class ShiftTradeNode(DjangoObjectType):
    class Meta:
        model = ShiftTrade
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return ShiftTrade.objects.get(pk=id)


class ShiftTradeOfferNode(DjangoObjectType):
    class Meta:
        model = ShiftTradeOffer
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return ShiftTradeOffer.objects.get(pk=id)


class ShiftSlotNode(DjangoObjectType):
    class Meta:
        model = ShiftSlot
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return ShiftSlot.objects.get(pk=id)


class ShiftSlotGroupNode(DjangoObjectType):
    class Meta:
        model = ShiftSlotGroup
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return ShiftSlotGroup.objects.get(pk=id)


class ShiftSlotGroupInterestNode(DjangoObjectType):
    class Meta:
        model = ShiftSlotGroupInterest
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return ShiftSlotGroupInterest.objects.get(pk=id)


class ShiftSlotGroupDayRuleNode(DjangoObjectType):
    class Meta:
        model = ShiftSlotGroupDayRule
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return ShiftSlotGroupDayRule.objects.get(pk=id)


# QUERIES
class ScheduleQuery(graphene.ObjectType):
    schedule = Node.Field(ScheduleNode)
    all_schedules = DjangoConnectionField(ScheduleNode)

    def resolve_all_schedules(self, info, *args, **kwargs):
        return Schedule.objects.all()


class ScheduleSlotTypeQuery(graphene.ObjectType):
    schedule_slot_type = Node.Field(ScheduleSlotTypeNode)
    all_schedule_slot_types = DjangoConnectionField(ScheduleSlotTypeNode)

    def resolve_all_schedule_slot_types(self, info, *args, **kwargs):
        return ScheduleSlotType.objects.all()


class ShiftQuery(graphene.ObjectType):
    shift = Node.Field(ShiftNode)
    all_shifts = DjangoConnectionField(ShiftNode)

    def resolve_all_shifts(self, info, *args, **kwargs):
        return Shift.objects.all()


class ShiftSlotQuery(graphene.ObjectType):
    shift_slot = Node.Field(ShiftSlotNode)
    all_shift_slots = DjangoConnectionField(ShiftSlotNode)
    my_shift_slots = graphene.NonNull(graphene.List(graphene.NonNull(ShiftSlotNode)))

    def resolve_all_shift_slots(self, info, *args, **kwargs):
        return ShiftSlot.objects.all()

    def resolve_my_shift_slots(self, info, *args, **kwargs):
        return ShiftSlot.objects.filter(filled_shift__user=info.context.user)


class ShiftTradeQuery(graphene.ObjectType):
    shift_trade = Node.Field(ShiftTradeNode)
    all_shift_trades = DjangoConnectionField(ShiftTradeNode)

    def resolve_all_shift_trades(self, info, *args, **kwargs):
        return ShiftTrade.objects.all()


class ShiftSlotGroupQuery(graphene.ObjectType):
    shift_slot_group = Node.Field(ShiftSlotGroupNode)
    all_shift_slot_groups = DjangoConnectionField(ShiftSlotGroupNode)

    def resolve_all_shift_slot_groups(self, info, *args, **kwargs):
        return ShiftSlotGroup.objects.all()


class ShiftSlotGroupInterestQuery(graphene.ObjectType):
    shift_slot_group_interest = Node.Field(ShiftSlotGroupInterestNode)
    all_shift_slot_group_interests = DjangoConnectionField(ShiftSlotGroupInterestNode)

    def resolve_all_shift_slot_group_interests(self, info, *args, **kwargs):
        return ShiftSlotGroupInterest.objects.all()


class ShiftTradeOfferQuery(graphene.ObjectType):
    shift_trade_offer = Node.Field(ShiftTradeOfferNode)
    all_shift_trade_offers = DjangoConnectionField(ShiftTradeOfferNode)

    def resolve_all_shift_Trade_offers(self, info, *args, **kwargs):
        return ShiftTradeOffer.objects.all()


class ShiftSlotGroupDayRuleQuery(graphene.ObjectType):
    shift_slot_group_day_rule = Node.Field(ShiftSlotGroupDayRuleNode)
    all_shift_slot_group_day_rules = DjangoConnectionField(ShiftSlotGroupDayRuleNode)

    def resolve_all_shift_slot_group_day_rules(self, info, *args, **kwargs):
        return ShiftSlotGroupDayRule.objects.all()


# MUTATIONS


class CreateScheduleMutation(DjangoCreateMutation):
    class Meta:
        model = Schedule


class PatchScheduleMutation(DjangoPatchMutation):
    class Meta:
        model = Schedule


class DeleteScheduleMutation(DjangoDeleteMutation):
    class Meta:
        model = Schedule


class CreateScheduleSlotTypeMutation(DjangoCreateMutation):
    class Meta:
        model = ScheduleSlotType


class PatchScheduleSlotTypeMutation(DjangoPatchMutation):
    class Meta:
        model = ScheduleSlotType


class DeleteScheduleSlotTypeMutation(DjangoDeleteMutation):
    class Meta:
        model = ScheduleSlotType


class CreateShiftMutation(DjangoCreateMutation):
    class Meta:
        model = Shift


class PatchShiftMutation(DjangoPatchMutation):
    class Meta:
        model = Shift


class DeleteShiftMutation(DjangoDeleteMutation):
    class Meta:
        model = Shift


class CreateShiftSlotMutation(DjangoCreateMutation):
    class Meta:
        model = ShiftSlot


class PatchShiftSlotMutation(DjangoPatchMutation):
    class Meta:
        model = ShiftSlot


class DeleteShiftSlotMutation(DjangoDeleteMutation):
    class Meta:
        model = ShiftSlot


class CreateShiftTradeMutation(DjangoCreateMutation):
    class Meta:
        model = ShiftTrade


class PatchShiftTradeMutation(DjangoPatchMutation):
    class Meta:
        model = ShiftTrade


class DeleteShiftTradeMutation(DjangoDeleteMutation):
    class Meta:
        model = ShiftTrade


class CreateShiftSlotGroupMutation(DjangoCreateMutation):
    class Meta:
        model = ShiftSlotGroup


class PatchShiftSlotGroupMutation(DjangoPatchMutation):
    class Meta:
        model = ShiftSlotGroup


class DeleteShiftSlotGroupMutation(DjangoDeleteMutation):
    class Meta:
        model = ShiftSlotGroup


class CreateShiftSlotGroupInterestMutation(DjangoCreateMutation):
    class Meta:
        model = ShiftSlotGroupInterest


class PatchShiftSlotGroupInterestMutation(DjangoPatchMutation):
    class Meta:
        model = ShiftSlotGroupInterest


class DeleteShiftSlotGroupInterestMutation(DjangoDeleteMutation):
    class Meta:
        model = ShiftSlotGroupInterest


class CreateShiftTradeOfferMutation(DjangoCreateMutation):
    class Meta:
        model = ShiftTradeOffer


class PatchShiftTradeOfferMutation(DjangoPatchMutation):
    class Meta:
        model = ShiftTradeOffer


class DeleteShiftTradeOfferMutation(DjangoDeleteMutation):
    class Meta:
        model = ShiftTradeOffer


class CreateShiftSlotGroupDayRuleMutation(DjangoCreateMutation):
    class Meta:
        model = ShiftSlotGroupDayRule


class PatchShiftSlotGroupDayRuleMutation(DjangoPatchMutation):
    class Meta:
        model = ShiftSlotGroupDayRule


class DeleteShiftSlotGroupDayRuleMutation(DjangoDeleteMutation):
    class Meta:
        model = ShiftSlotGroupDayRule


class SchedulesMutations(graphene.ObjectType):
    create_schedule = CreateScheduleMutation.Field()
    patch_schedule = PatchScheduleMutation.Field()
    delete_schedule = DeleteScheduleMutation.Field()

    create_schedule_slot_type = CreateScheduleSlotTypeMutation.Field()
    patch_schedule_slot_type = PatchScheduleSlotTypeMutation.Field()
    delete_schedule_slot_type = DeleteScheduleSlotTypeMutation.Field()

    create_shift = CreateShiftMutation.Field()
    patch_shift = PatchShiftMutation.Field()
    delete_shift = DeleteShiftMutation.Field()

    create_shift_slot = CreateShiftSlotMutation.Field()
    patch_shift_slot = PatchShiftSlotMutation.Field()
    delete_shift_slot = DeleteShiftSlotMutation.Field()

    create_shift_trade = CreateShiftTradeMutation.Field()
    patch_shift_trade = PatchShiftTradeMutation.Field()
    delete_shift_trade = DeleteShiftTradeMutation.Field()

    create_shift_slot_group = CreateShiftSlotGroupMutation.Field()
    patch_shift_slot_group = PatchShiftSlotGroupMutation.Field()
    delete_shift_slot_group = DeleteShiftSlotGroupMutation.Field()

    create_shift_slot_group_interest = CreateShiftSlotGroupInterestMutation.Field()
    patch_shift_slot_group_interest = PatchShiftSlotGroupInterestMutation.Field()
    delete_shift_slot_group_interest = DeleteShiftSlotGroupInterestMutation.Field()

    create_shift_trade_offer = CreateShiftTradeOfferMutation.Field()
    patch_shift_trade_offer = PatchShiftTradeOfferMutation.Field()
    delete_shift_trade_offer = DeleteShiftTradeOfferMutation.Field()

    create_shift_slot_group_day_rule = CreateShiftSlotGroupDayRuleMutation.Field()
    patch_shift_slot_group_day_rule = PatchShiftSlotGroupDayRuleMutation.Field()
    delete_shift_slot_group_day_rule = DeleteShiftSlotGroupDayRuleMutation.Field()
