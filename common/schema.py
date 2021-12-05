import graphene
from summaries.schema import SummaryNode
from summaries.models import Summary
from quotes.schema import QuoteNode
from quotes.models import Quote
from users.schema import UserNode
from economy.models import SociBankAccount


class DashboardData(graphene.ObjectType):
    last_quotes = graphene.List(QuoteNode)
    last_summaries = graphene.List(SummaryNode)
    wanted_list = graphene.List(UserNode)


class DashboardQuery(graphene.ObjectType):
    dashboard_data = graphene.Field(DashboardData)

    def resolve_dashboard_data(self, info, *args, **kwargs):
        quotes = Quote.objects.filter(verified_by__isnull=False).order_by("-created")[
            :5
        ]
        summaries = Summary.objects.all().order_by("-date")[:6]
        wanted = SociBankAccount.get_wanted_list()
        return DashboardData(
            last_quotes=quotes, last_summaries=summaries, wanted_list=wanted
        )
