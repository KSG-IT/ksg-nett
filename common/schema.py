import graphene
from summaries.schema import SummaryNode
from summaries.models import Summary
from quotes.schema import QuoteNode
from quotes.models import Quote
from users.schema import UserNode
from economy.models import SociBankAccount, Deposit


class DashboardData(graphene.ObjectType):
    last_quotes = graphene.NonNull(graphene.List(graphene.NonNull(QuoteNode)))
    last_summaries =graphene.NonNull(graphene.List(graphene.NonNull(SummaryNode)))
    wanted_list = graphene.NonNull(graphene.List(graphene.NonNull(UserNode)))


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
        quotes = Quote.objects.filter(verified_by__isnull=False).order_by(
            "-created_at"
        )[:5]
        summaries = Summary.objects.all().order_by("-date")[:6]
        wanted = SociBankAccount.get_wanted_list()
        return DashboardData(
            last_quotes=quotes, last_summaries=summaries, wanted_list=wanted
        )
