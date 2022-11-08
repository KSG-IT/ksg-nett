import graphene
import jwt
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from graphql import GraphQLError

from users.schema import UserNode
from users.models import User
from django.contrib.auth import authenticate
from login.util import create_jwt_token_for_user, send_password_reset_email


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


class ResetMyPasswordMutation(graphene.Mutation):
    """
    Mutation used to reset a users password. The user is searched for, and then sent a reset email.
    This does not actually reset the password.
    """

    class Arguments:
        username = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, username):
        user = User.objects.filter(Q(username=username) | Q(email=username)).first()

        if user:
            jwt_reset_token = jwt.encode(
                {
                    "action": "reset_password",
                    "user_id": user.id,
                    "iss": "KSG-nett",
                    "iat": timezone.now(),
                    "exp": timezone.now() + timezone.timedelta(hours=24),
                },
                settings.AUTH_JWT_SECRET,
                algorithm=settings.AUTH_JWT_METHOD,
            )
            send_password_reset_email(user, jwt_reset_token)

        # Always return true, so that we don't leak information about which users exist.
        return ResetMyPasswordMutation(ok=True)


class ResetPasswordByTokenMutation(graphene.Mutation):
    """
    Mutation used as the final step in a user initiated password reset request.
    The user has received a token-url, which leads to a reset-password page on the frontend.
    This page calls this endpoint, supplying the token to verify the password reset request.
    The mutation also returns a login-token back to the user, on succesful verification and
    password reset.
    """

    class Arguments:
        token = graphene.String(required=True)
        new_password = graphene.String(required=True)

    ok = graphene.Boolean()
    login_token = graphene.String()

    def mutate(self, info, token, new_password):
        try:
            data = jwt.decode(
                token, settings.AUTH_JWT_SECRET, algorithms=[settings.AUTH_JWT_METHOD]
            )
            user_id = data.get("user_id")
            action = data.get("action")

            if action != "reset_password":
                raise GraphQLError("Token had bad action. Expected 'reset_password'.")

            user = User.objects.get(pk=user_id)
            user.set_password(new_password)
            user.needs_new_password = False
            user.is_active = True
            user.save()

            return ResetPasswordByTokenMutation(
                ok=True, login_token=create_jwt_token_for_user(user)
            )
        except User.DoesNotExist:
            raise GraphQLError("Invalid token.")
        except jwt.ExpiredSignatureError:
            raise GraphQLError("Token has expired.")
        except jwt.DecodeError:
            raise GraphQLError("Invalid token.")


class LoginMutations(graphene.ObjectType):
    login = LoginMutation.Field()
    reset_my_password = ResetMyPasswordMutation.Field()
    reset_password_by_token = ResetPasswordByTokenMutation.Field()
