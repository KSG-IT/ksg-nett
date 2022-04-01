import graphene
from admissions.schema import AdmissionQuery, ApplicantQuery, AdmissionsMutations
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
from schedules.schemas.schema_schedules import (
    ShiftQuery,
    ScheduleQuery,
    SchedulesMutations,
)

from sensors.schema import SensorMeasurementQuery, SensorsMutations
from summaries.schema import SummaryQuery, SummariesMutations
from events.schema import EventQuery, EventMutations

class Query(
    AdmissionQuery,
    ApplicantQuery,
    AuthenticationQuery,
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
    ShiftQuery,
    ScheduleQuery,
    SensorMeasurementQuery,
    SummaryQuery,
    QuoteQuery,
    EventQuery,
    graphene.ObjectType,
):
    pass


class Mutation(
    AdmissionsMutations,
    EconomyMutations,
    LoginMutations,
    OrganizationMutations,
    UserMutations,
    QuotesMutations,
    SchedulesMutations,
    SensorsMutations,
    SummariesMutations,
    EventMutations,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
