import json

from channels.generic.websocket import  AsyncWebsocketConsumer
from django.utils import timezone
from django.utils.html import strip_tags, escape

from chat import redis
from users.models import User


class ChatConsumer(AsyncWebsocketConsumer):

    def get_user_object(self):
        return {
            'id': self.user.id,
            'name': self.user.get_full_name(),
            'img': self.user.profile_image_url
        }


    async def connect(self):
        self.room_name = "ksg"
        self.room_group_name = "ksg-chat"
        self.user: User = self.scope['user']

        all_current_users = redis.get_all_connected_users()
        all_old_messages = redis.get_all_old_messages()

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_joined",
                "user": self.get_user_object()
            }
        )

        await self.accept()
        await self.send(text_data=json.dumps({
            "type": "initialize",
            "users": all_current_users,
            "messages": all_old_messages
        }))

        redis.add_user_to_chat(self.get_user_object())

    async def disconnect(self, code):
        redis.remove_user_from_chat(self.get_user_object())

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_left",
                "user": self.user.id
            }
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        timestamp = timezone.now().strftime("%A %H:%M")

        if message == "":
            return

        message = escape(message)

        full_message_obj = {
            "message": message,
            "user": self.get_user_object(),
            "timestamp": timestamp
        }

        redis.add_message(full_message_obj)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                **full_message_obj
            }
        )

    async def chat_message(self, event):
        message = event["message"]
        user = event["user"]
        timestamp = event["timestamp"]

        await self.send(text_data=json.dumps({
            "type": "message",
            "message": message,
            "user": user,
            "timestamp": timestamp
        }))


    async def user_joined(self, event):
        user = event["user"]

        await self.send(text_data=json.dumps({
            "type": "user-joined",
            "user": user
        }))


    async def user_left(self, event):
        user = event["user"]

        await self.send(text_data=json.dumps({
            "type": "user-left",
            "user": user
        }))
