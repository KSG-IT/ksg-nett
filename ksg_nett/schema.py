import graphene
from admissions.schema import (
    AdmissionQuery,
    ApplicantQuery,
    AdmissionsMutations,
    InterviewLocationQuery,
    InterviewQuery,
)
from common.schema import DashboardQuery, SidebarQuery
from users.schema import UserQuery, UserMutations
from login.schema import LoginMutations, AuthenticationQuery
from economy.schema import (
    SociProductQuery,
    SociBankAccountQuery,
    DepositQuery,
    ProductOrderQuery,
    SociOrderSessionQuery,
    EconomyMutations,
    SociSessionQuery,
)
from bar_tab.schema import (
    BarTabQuery,
    BarTabMutations,
)
from organization.schema import (
    InternalGroupQuery,
    InternalGroupPositionQuery,
    InternalGroupPositionMembershipQuery,
    OrganizationMutations,
    InternalGroupUserHighlightQuery,
)
from quotes.schema import QuoteQuery, QuotesMutations
from schedules.schemas.schedules import (
    ShiftQuery,
    ScheduleQuery,
    SchedulesMutations,
)
from schedules.schemas.templates import ScheduleTemplateQuery, ScheduleTemplateMutations

from sensors.schema import SensorMeasurementQuery, SensorsMutations
from summaries.schema import SummaryQuery, SummariesMutations
from handbook.schema import DocumentQueries, HandbookMutations


class Query(
    AdmissionQuery,
    ApplicantQuery,
    AuthenticationQuery,
    BarTabQuery,
    DashboardQuery,
    DepositQuery,
    DocumentQueries,
    ProductOrderQuery,
    SidebarQuery,
    SociBankAccountQuery,
    SociProductQuery,
    SociSessionQuery,
    SociOrderSessionQuery,
    UserQuery,
    InternalGroupQuery,
    InternalGroupPositionQuery,
    InternalGroupPositionMembershipQuery,
    InternalGroupUserHighlightQuery,
    InterviewQuery,
    InterviewLocationQuery,
    ShiftQuery,
    ScheduleQuery,
    ScheduleTemplateQuery,
    SensorMeasurementQuery,
    SummaryQuery,
    QuoteQuery,
    graphene.ObjectType,
):
    pass


class Mutation(
    AdmissionsMutations,
    BarTabMutations,
    EconomyMutations,
    HandbookMutations,
    LoginMutations,
    OrganizationMutations,
    UserMutations,
    QuotesMutations,
    SchedulesMutations,
    ScheduleTemplateMutations,
    SensorsMutations,
    SummariesMutations,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
