import graphene
from users.schema import UserQuery, UserMutations


class Query(
    UserQuery,
    graphene.ObjectType,
):
    pass


class Mutation(
    UserMutations,
    graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
