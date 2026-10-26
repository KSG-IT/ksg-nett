import graphene
from django.conf import settings
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch
from django.db.models.functions import Coalesce
from django.utils import timezone
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.util import disambiguate_id
from graphql_relay import to_global_id

from chat.models import Chat, ChatMembership, ChatMessage
from chat.notifications import notify_added, notify_new_chat, notify_new_message
from chat.utils import (
    add_members,
    create_mega_chat,
    fetch_chat_for_shift,
    get_chat,
    is_online,
    joinable_shift_chats,
    mark_read,
    mega_chat_preview,
    ping,
    readable_chat,
    send_chat_message,
    set_muted,
    total_unread,
    with_unread_count,
)
from common.decorators import gql_feature_flag_required, gql_login_required
from common.exceptions import IllegalOperation
from schedules.models import Shift
from users.schema import UserNode

HIDDEN_MESSAGE_TEXT = "Melding fjernet av moderator"
MAX_MESSAGES_PER_REQUEST = 100


def chat_enabled(func):
    """Every chat field needs a logged in user and the `chat` feature flag."""
    return gql_login_required()(
        gql_feature_flag_required(settings.CHAT_FEATURE_FLAG)(func)
    )


class ChatMessageNode(DjangoObjectType):
    class Meta:
        model = ChatMessage
        interfaces = (Node,)
        fields = ("id", "sender", "role", "body", "created_at")

    hidden = graphene.Boolean(required=True)

    def resolve_hidden(self: ChatMessage, info):
        return self.hidden_at is not None

    def resolve_body(self: ChatMessage, info):
        return HIDDEN_MESSAGE_TEXT if self.hidden_at else self.body


class ChatMemberType(graphene.ObjectType):
    user = graphene.Field(UserNode, required=True)
    online = graphene.Boolean(required=True)
    last_read_message_id = graphene.ID(
        description="The newest message this member has read. Null for non-members."
    )


class ChatNode(DjangoObjectType):
    class Meta:
        model = Chat
        interfaces = (Node,)
        fields = ("id", "name", "created_at", "closes_at", "members_editable")

    closed = graphene.Boolean(required=True)
    unread_count = graphene.Int(required=True)
    last_message = graphene.Field(ChatMessageNode)
    members = graphene.List(graphene.NonNull(ChatMemberType), required=True)
    online_count = graphene.Int(required=True)
    muted = graphene.Boolean(
        required=True, description="The viewer muted message pushes for this chat."
    )

    def resolve_closed(self: Chat, info):
        return timezone.now() > self.closes_at

    def resolve_unread_count(self: Chat, info):
        user = info.context.user
        if hasattr(self, "unread"):
            return self.unread
        if not any(m.user_id == user.pk for m in self.memberships.all()):
            return 0
        annotated = with_unread_count(Chat.objects.filter(pk=self.pk), user).get()
        return annotated.unread

    def resolve_muted(self: Chat, info):
        if hasattr(self, "muted"):
            return self.muted
        return with_muted(Chat.objects.filter(pk=self.pk), info.context.user)[0].muted

    def resolve_last_message(self: Chat, info):
        if hasattr(self, "last_message_cache"):
            return self.last_message_cache
        return self.messages.select_related("sender").order_by("-id").first()

    def _visible_members(self: Chat, info):
        """
        Presence and read markers show only to members. A superuser who reads
        a chat they are not in sees the users, but no presence.
        """
        memberships = list(self.memberships.all())
        viewer_is_member = any(m.user_id == info.context.user.pk for m in memberships)
        return memberships, viewer_is_member

    def resolve_members(self: Chat, info):
        memberships, viewer_is_member = ChatNode._visible_members(self, info)
        now = timezone.now()
        return [
            ChatMemberType(
                user=m.user,
                online=viewer_is_member and is_online(m, now),
                last_read_message_id=(
                    to_global_id("ChatMessageNode", m.last_read_message_id)
                    if viewer_is_member and m.last_read_message_id
                    else None
                ),
            )
            for m in memberships
        ]

    def resolve_online_count(self: Chat, info):
        memberships, viewer_is_member = ChatNode._visible_members(self, info)
        if not viewer_is_member:
            return 0
        now = timezone.now()
        return sum(1 for m in memberships if is_online(m, now))


def prefetch_members(chats):
    return chats.prefetch_related(
        Prefetch("memberships", queryset=ChatMembership.objects.select_related("user"))
    )


def attach_last_messages(chats):
    """Load the newest message of each chat in one query."""
    chats = list(chats)
    ids = [chat.last_message_id for chat in chats if chat.last_message_id]
    messages = {
        message.pk: message
        for message in ChatMessage.objects.filter(pk__in=ids).select_related("sender")
    }
    for chat in chats:
        chat.last_message_cache = messages.get(chat.last_message_id)
    return chats


def with_muted(chats, user):
    """Annotate each chat with `muted` for the user, in the same query."""
    return chats.annotate(
        muted=Exists(
            ChatMembership.objects.filter(chat=OuterRef("pk"), user=user, muted=True)
        )
    )


def inbox(chats, user):
    """Newest message first. A chat without a message sorts by its creation."""
    chats = with_muted(with_unread_count(prefetch_members(chats), user), user)
    chats = chats.order_by(Coalesce("last_message_at", "created_at").desc(), "-id")
    return attach_last_messages(chats)


class JoinableShiftChatType(graphene.ObjectType):
    shift = graphene.Field("schedules.schemas.schedules.ShiftNode", required=True)
    user_count = graphene.Int(required=True)
    chat = graphene.Field(ChatNode, description="Null until somebody joins.")


class MegaChatShiftType(graphene.ObjectType):
    shift = graphene.Field("schedules.schemas.schedules.ShiftNode", required=True)
    user_count = graphene.Int(required=True)


class MegaChatPreviewType(graphene.ObjectType):
    open = graphene.Boolean(
        required=True, description="True on Friday and Saturday evenings."
    )
    user_count = graphene.Int(
        required=True, description="Users on duty now, each counted once."
    )
    shifts = graphene.List(graphene.NonNull(MegaChatShiftType), required=True)


class ChatQuery(graphene.ObjectType):
    my_chats = graphene.List(graphene.NonNull(ChatNode), required=True)
    all_chats = graphene.List(
        graphene.NonNull(ChatNode),
        required=True,
        description="Every chat. Superusers only.",
    )
    chat = graphene.Field(ChatNode, chat_id=graphene.ID(required=True))
    chat_messages = graphene.List(
        graphene.NonNull(ChatMessageNode),
        required=True,
        chat_id=graphene.ID(required=True),
        after_id=graphene.ID(
            description="Only messages after this one. Used for polling."
        ),
        limit=graphene.Int(),
    )
    unread_chat_count = graphene.Int(required=True)
    joinable_shift_chats = graphene.List(
        graphene.NonNull(JoinableShiftChatType), required=True
    )
    mega_chat_preview = graphene.Field(
        MegaChatPreviewType,
        required=True,
        description="Who a new mega chat would hold. Needs chat.create_mega_chat.",
    )

    @chat_enabled
    def resolve_my_chats(self, info):
        user = info.context.user
        return inbox(Chat.objects.filter(memberships__user=user), user)

    @chat_enabled
    def resolve_all_chats(self, info):
        user = info.context.user
        if not user.is_superuser:
            raise IllegalOperation("You are not permitted to view this")
        return inbox(Chat.objects.all(), user)

    @chat_enabled
    def resolve_chat(self, info, chat_id):
        user = info.context.user
        chat = readable_chat(user, chat_id)
        return inbox(Chat.objects.filter(pk=chat.pk), user)[0]

    @chat_enabled
    def resolve_chat_messages(self, info, chat_id, after_id=None, limit=50):
        chat = readable_chat(info.context.user, chat_id)
        limit = max(1, min(limit, MAX_MESSAGES_PER_REQUEST))
        messages = chat.messages.select_related("sender")
        if after_id:
            return messages.filter(id__gt=disambiguate_id(after_id)).order_by("id")[
                :limit
            ]
        # The first load: the newest messages, oldest first
        return list(messages.order_by("-id")[:limit])[::-1]

    @chat_enabled
    def resolve_unread_chat_count(self, info):
        return total_unread(info.context.user)

    @chat_enabled
    def resolve_joinable_shift_chats(self, info):
        return [
            JoinableShiftChatType(shift=shift, user_count=shift.user_count, chat=chat)
            for shift, chat in joinable_shift_chats(info.context.user)
        ]

    @chat_enabled
    def resolve_mega_chat_preview(self, info):
        preview = mega_chat_preview(info.context.user)
        return MegaChatPreviewType(
            open=preview["open"],
            user_count=preview["user_count"],
            shifts=[
                MegaChatShiftType(shift=shift, user_count=user_count)
                for shift, user_count in preview["shifts"]
            ],
        )


class JoinShiftChatMutation(graphene.Mutation):
    class Arguments:
        shift_id = graphene.ID(required=True)

    chat = graphene.Field(ChatNode)
    created = graphene.Boolean()

    @chat_enabled
    def mutate(self, info, shift_id):
        try:
            shift = Shift.objects.get(pk=disambiguate_id(shift_id))
        except (Shift.DoesNotExist, ValueError):
            raise IllegalOperation("Shift does not exist")
        user = info.context.user
        chat, created = fetch_chat_for_shift(user, shift)
        if created:
            transaction.on_commit(lambda: notify_new_chat(chat, user))
        return JoinShiftChatMutation(chat=chat, created=created)


class CreateMegaChatMutation(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)

    chat = graphene.Field(ChatNode)

    @chat_enabled
    def mutate(self, info, name):
        user = info.context.user
        chat = create_mega_chat(user, name)
        transaction.on_commit(lambda: notify_new_chat(chat, user))
        return CreateMegaChatMutation(chat=chat)


class AddChatMembersMutation(graphene.Mutation):
    class Arguments:
        chat_id = graphene.ID(required=True)
        user_ids = graphene.List(graphene.NonNull(graphene.ID), required=True)

    chat = graphene.Field(ChatNode)
    added_count = graphene.Int()

    @chat_enabled
    def mutate(self, info, chat_id, user_ids):
        chat = get_chat(chat_id)
        try:
            ids = [int(disambiguate_id(user_id)) for user_id in user_ids]
        except ValueError:
            raise IllegalOperation("Invalid user id")
        user = info.context.user
        added = add_members(user, chat, ids)
        transaction.on_commit(lambda: notify_added(chat, added, user))
        return AddChatMembersMutation(chat=chat, added_count=len(added))


class SendChatMessageMutation(graphene.Mutation):
    class Arguments:
        chat_id = graphene.ID(required=True)
        body = graphene.String(required=True)

    message = graphene.Field(ChatMessageNode)

    @chat_enabled
    def mutate(self, info, chat_id, body):
        message = send_chat_message(info.context.user, get_chat(chat_id), body)
        transaction.on_commit(lambda: notify_new_message(message))
        return SendChatMessageMutation(message=message)


class MarkChatReadMutation(graphene.Mutation):
    class Arguments:
        chat_id = graphene.ID(required=True)
        message_id = graphene.ID(required=True)

    changed = graphene.Boolean()

    @chat_enabled
    def mutate(self, info, chat_id, message_id):
        try:
            message_pk = int(disambiguate_id(message_id))
        except ValueError:
            raise IllegalOperation("Invalid message id")
        changed = mark_read(info.context.user, get_chat(chat_id), message_pk)
        return MarkChatReadMutation(changed=changed)


class PingChatMutation(graphene.Mutation):
    """The SPA calls this while a chat is open, to show the member as online."""

    class Arguments:
        chat_id = graphene.ID(required=True)

    recorded = graphene.Boolean()

    @chat_enabled
    def mutate(self, info, chat_id):
        return PingChatMutation(recorded=ping(info.context.user, get_chat(chat_id)))


class SetChatMutedMutation(graphene.Mutation):
    """Mute or unmute message pushes for one chat. Being added still pushes."""

    class Arguments:
        chat_id = graphene.ID(required=True)
        muted = graphene.Boolean(required=True)

    chat = graphene.Field(ChatNode)

    @chat_enabled
    def mutate(self, info, chat_id, muted):
        user = info.context.user
        chat = get_chat(chat_id)
        set_muted(user, chat, muted)
        return SetChatMutedMutation(
            chat=inbox(Chat.objects.filter(pk=chat.pk), user)[0]
        )


class ChatMutations(graphene.ObjectType):
    join_shift_chat = JoinShiftChatMutation.Field()
    create_mega_chat = CreateMegaChatMutation.Field()
    add_chat_members = AddChatMembersMutation.Field()
    send_chat_message = SendChatMessageMutation.Field()
    mark_chat_read = MarkChatReadMutation.Field()
    ping_chat = PingChatMutation.Field()
    set_chat_muted = SetChatMutedMutation.Field()
