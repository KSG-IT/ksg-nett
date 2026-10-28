import graphene
from django.conf import settings

from common.decorators import gql_feature_flag_required, gql_login_required
from common.exceptions import IllegalOperation
from push.models import PushSubscription
from push.utils import is_push_service_endpoint
from users.schema import UserNode


def push_enabled(func):
    """Every push field needs a logged in user and the push feature flag."""
    return gql_login_required()(
        gql_feature_flag_required(settings.PUSH_FEATURE_FLAG)(func)
    )


class PushConfigType(graphene.ObjectType):
    vapid_public_key = graphene.String(
        description="The applicationServerKey for pushManager.subscribe."
    )


class PushQuery(graphene.ObjectType):
    push_config = graphene.Field(PushConfigType, required=True)

    @push_enabled
    def resolve_push_config(self, info):
        return PushConfigType(vapid_public_key=settings.VAPID_PUBLIC_KEY or None)


class RegisterPushSubscriptionMutation(graphene.Mutation):
    """
    Save the subscription of this browser for the caller. The same endpoint
    again updates the row, also when another user logged in on the device.
    """

    class Arguments:
        endpoint = graphene.String(required=True)
        p256dh = graphene.String(required=True)
        auth = graphene.String(required=True)
        user_agent = graphene.String()

    ok = graphene.Boolean()

    @push_enabled
    def mutate(self, info, endpoint, p256dh, auth, user_agent=None):
        max_length = PushSubscription._meta.get_field("endpoint").max_length
        if len(endpoint) > max_length or not is_push_service_endpoint(endpoint):
            raise IllegalOperation("Invalid push endpoint")
        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": info.context.user,
                "p256dh": p256dh,
                "auth": auth,
                "user_agent": (user_agent or "")[:300],
                "vapid_public_key": settings.VAPID_PUBLIC_KEY,
            },
        )
        return RegisterPushSubscriptionMutation(ok=True)


class RemovePushSubscriptionMutation(graphene.Mutation):
    """Delete the subscription if it belongs to the caller. Ok also when not."""

    class Arguments:
        endpoint = graphene.String(required=True)

    ok = graphene.Boolean()

    @push_enabled
    def mutate(self, info, endpoint):
        PushSubscription.objects.filter(
            endpoint=endpoint, user=info.context.user
        ).delete()
        return RemovePushSubscriptionMutation(ok=True)


class SetChatNotificationsMutation(graphene.Mutation):
    """
    The chat push settings of the caller. They apply on every device.
    Replaced by setPushSettings; remove when the SPA no longer calls it.
    """

    class Arguments:
        on_message = graphene.Boolean(required=True)
        on_added = graphene.Boolean(required=True)

    user = graphene.Field(UserNode)

    @push_enabled
    def mutate(self, info, on_message, on_added):
        user = info.context.user
        user.notify_on_chat_message = on_message
        user.notify_on_chat_added = on_added
        user.save(update_fields=["notify_on_chat_message", "notify_on_chat_added"])
        return SetChatNotificationsMutation(user=user)


# Argument name -> User field. A new push setting is one more line here.
PUSH_SETTINGS = {
    "on_chat_message": "notify_on_chat_message",
    "on_chat_added": "notify_on_chat_added",
    "on_deposit": "push_on_deposit",
    "on_quote": "push_on_quote",
    "on_shift": "push_on_shift",
    "on_order_session": "push_on_order_session",
}


class SetPushSettingsMutation(graphene.Mutation):
    """
    The push settings of the caller. They apply on every device. Only the
    given settings change.
    """

    class Arguments:
        on_chat_message = graphene.Boolean()
        on_chat_added = graphene.Boolean()
        on_deposit = graphene.Boolean()
        on_quote = graphene.Boolean()
        on_shift = graphene.Boolean()
        on_order_session = graphene.Boolean()

    user = graphene.Field(UserNode)

    @push_enabled
    def mutate(self, info, **values):
        user = info.context.user
        fields = []
        for argument, value in values.items():
            if value is None:
                continue
            setattr(user, PUSH_SETTINGS[argument], value)
            fields.append(PUSH_SETTINGS[argument])
        if fields:
            user.save(update_fields=fields)
        return SetPushSettingsMutation(user=user)


class PushMutations(graphene.ObjectType):
    register_push_subscription = RegisterPushSubscriptionMutation.Field()
    remove_push_subscription = RemovePushSubscriptionMutation.Field()
    set_chat_notifications = SetChatNotificationsMutation.Field()
    set_push_settings = SetPushSettingsMutation.Field()
