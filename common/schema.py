import graphene
from django.utils import timezone

from admissions.models import Admission
from schedules.schemas.schedules import ShiftSlotNode
from summaries.schema import SummaryNode
from summaries.models import Summary
from quotes.schema import QuoteNode
from quotes.models import Quote
from users.schema import UserNode
from economy.models import SociBankAccount, Deposit


class DashboardData(graphene.ObjectType):
    last_quotes = graphene.NonNull(graphene.List(graphene.NonNull(QuoteNode)))
    last_summaries = graphene.NonNull(graphene.List(graphene.NonNull(SummaryNode)))
    wanted_list = graphene.NonNull(graphene.List(graphene.NonNull(UserNode)))
    my_upcoming_shifts = graphene.NonNull(
        graphene.List(graphene.NonNull(ShiftSlotNode))
    )
    soci_order_session = graphene.Field("economy.schema.SociOrderSessionNode")
    show_newbies = graphene.Boolean()


class SidebarData(graphene.ObjectType):
    pending_quotes = graphene.Int()
    pending_deposits = graphene.Int()


class SidebarQuery(graphene.ObjectType):
    sidebar_data = graphene.Field(SidebarData)

    def resolve_sidebar_data(self, info, *args, **kwargs):
        pending_quotes = Quote.get_pending_quotes().count()
        pending_deposits = Deposit.get_pending_deposits().count()
        return SidebarData(
            pending_quotes=pending_quotes, pending_deposits=pending_deposits
        )


class DashboardQuery(graphene.ObjectType):
    dashboard_data = graphene.Field(graphene.NonNull(DashboardData))

    def resolve_dashboard_data(self, info, *args, **kwargs):
        me = info.context.user
        quotes = Quote.objects.filter(approved=True).order_by("-created_at")[:5]
        summaries = Summary.objects.all().order_by("-date")[:6]
        wanted = SociBankAccount.get_wanted_list()
        upcoming_shifts = me.future_shifts
        soci_order_session = me.get_invited_soci_order_session

        admission = Admission.get_last_closed_admission()
        if not admission:
            show_newbies = False
        else:
            delta_since_closed = timezone.now() - admission.closed_at
            show_newbies = delta_since_closed.days < 30

        return DashboardData(
            last_quotes=quotes,
            last_summaries=summaries,
            wanted_list=wanted,
            my_upcoming_shifts=upcoming_shifts,
            soci_order_session=soci_order_session,
            show_newbies=show_newbies,
        )
