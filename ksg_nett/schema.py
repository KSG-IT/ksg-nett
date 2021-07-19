import graphene
from admissions.schema import AdmissionQuery, ApplicantQuery, AdmissionsMutations
from users.schema import UserQuery, UserMutations
from login.schema import LoginMutations, AuthenticationQuery
from economy.schema import (
    SociProductQuery,
    SociBankAccountQuery,
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


class Query(
    AdmissionQuery,
    ApplicantQuery,
    AuthenticationQuery,
    ProductOrderQuery,
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
    QuoteQuery,
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
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
