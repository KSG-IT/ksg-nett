import graphene
from admissions.schema import AdmissionQuery, ApplicantQuery, AdmissionsMutations
from users.schema import UserQuery, UserMutations
from login.schema import LoginMutations, AuthenticationQuery


class Query(
    AdmissionQuery,
    ApplicantQuery,
    AuthenticationQuery,
    UserQuery,
    graphene.ObjectType,
):
    pass


class Mutation(
    AdmissionsMutations,
    UserMutations,
    LoginMutations,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
