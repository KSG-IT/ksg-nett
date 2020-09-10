import json
import logging
from typing import List

import redis
from django.conf import settings
from redis import RedisError

CHAT_STATE_STORAGE_ENABLED = True
CHAT_ROOM_USERS_REDIS_KEY = "chat-room-users"
CHAT_ROOM_OLD_MESSAGES_KEY = "chat-room-messages"

CHAT_ROOM_MAX_MESSAGES = 50

try:
    db = redis.Redis(
        host=settings.REDIS.get("host"),
        port=settings.REDIS.get("port"),
        db=settings.CHAT_STATE_REDIS_DB,
    )
except RedisError as e:
    logging.warning(f"Unable to connect to Redis. Failed with {e}.")
    CHAT_STATE_STORAGE_ENABLED = False


def add_user_to_chat(user: dict):
    if not CHAT_STATE_STORAGE_ENABLED:
        return

    db.sadd(CHAT_ROOM_USERS_REDIS_KEY, json.dumps(user))


def remove_user_from_chat(user):
    if not CHAT_STATE_STORAGE_ENABLED:
        return

    db.srem(CHAT_ROOM_USERS_REDIS_KEY, json.dumps(user))


def get_all_connected_users() -> List[dict]:
    users_raw = db.smembers(CHAT_ROOM_USERS_REDIS_KEY)
    users_raw = [json.loads(user) for user in users_raw]

    return users_raw


def add_message(message: dict):
    # We create a FIFO queue containing at most 50 elements.
    db.rpush(CHAT_ROOM_OLD_MESSAGES_KEY, json.dumps(message))

    queue_length = db.llen(CHAT_ROOM_OLD_MESSAGES_KEY)
    if queue_length > CHAT_ROOM_MAX_MESSAGES:
        db.ltrim(CHAT_ROOM_OLD_MESSAGES_KEY, queue_length - CHAT_ROOM_MAX_MESSAGES, -1)


def get_all_old_messages() -> List[dict]:
    messages_raw = db.lrange(CHAT_ROOM_OLD_MESSAGES_KEY, 0, -1)
    return [
        json.loads(message)
        for message in messages_raw
    ]
