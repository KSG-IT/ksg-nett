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
    EconomyMutations,
    SociSessionQuery,
)
from bar_tab.schema import (
    BarTabQuery,
    BarTabMutations,
)
from organization.schema import (
    CommissionQuery,
    CommissionMembershipQuery,
    CommitteeQuery,
    InternalGroupQuery,
    InternalGroupPositionQuery,
    InternalGroupPositionMembershipQuery,
    OrganizationMutations,
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
from events.schema import EventQuery, EventMutations


class Query(
    AdmissionQuery,
    ApplicantQuery,
    AuthenticationQuery,
    BarTabQuery,
    DashboardQuery,
    DepositQuery,
    ProductOrderQuery,
    SidebarQuery,
    SociBankAccountQuery,
    SociProductQuery,
    SociSessionQuery,
    UserQuery,
    CommissionQuery,
    CommissionMembershipQuery,
    CommitteeQuery,
    InternalGroupQuery,
    InternalGroupPositionQuery,
    InternalGroupPositionMembershipQuery,
    InterviewQuery,
    InterviewLocationQuery,
    ShiftQuery,
    ScheduleQuery,
    ScheduleTemplateQuery,
    SensorMeasurementQuery,
    SummaryQuery,
    QuoteQuery,
    EventQuery,
    graphene.ObjectType,
):
    pass


class Mutation(
    AdmissionsMutations,
    BarTabMutations,
    EconomyMutations,
    LoginMutations,
    OrganizationMutations,
    UserMutations,
    QuotesMutations,
    SchedulesMutations,
    ScheduleTemplateMutations,
    SensorsMutations,
    SummariesMutations,
    EventMutations,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
