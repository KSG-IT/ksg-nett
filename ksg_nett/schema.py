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


class Query(
    AdmissionQuery,
    ApplicantQuery,
    AuthenticationQuery,
    ProductOrderQuery,
    SociBankAccountQuery,
    SociProductQuery,
    SociSessionQuery,
    UserQuery,
    graphene.ObjectType,
):
    pass


class Mutation(
    AdmissionsMutations,
    EconomyMutations,
    LoginMutations,
    UserMutations,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
