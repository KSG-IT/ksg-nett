import graphene
from users.schema import UserNode
from django.contrib.auth import authenticate
from login.util import create_jwt_token_for_user


class LoginMutation(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        password = graphene.String(required=True)

    ok = graphene.Boolean(required=True)
    token = graphene.String(required=False)
    user = graphene.Field(UserNode, required=False)

    def mutate(self, info, username, password):
        user = authenticate(info.context, username=username, password=password)
        if user is None:
            return LoginMutation(ok=False, token=None, user=None)

        token = create_jwt_token_for_user(user)

        return LoginMutation(ok=True, token=token, user=user)


class VerifyResetPasswordTokenNode(graphene.ObjectType):
    valid = graphene.Boolean()
    reason = graphene.String(required=False)


class AuthenticationQuery(graphene.ObjectType):
    is_logged_in = graphene.Boolean()

    def resolve_is_logged_in(self, info, **args):
        return info.context.user.is_authenticated

    verify_reset_password_token = graphene.Field(
        VerifyResetPasswordTokenNode, args={"token": graphene.String()}
    )


class LoginMutations(graphene.ObjectType):
    login = LoginMutation.Field()
