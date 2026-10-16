from datetime import timedelta

# A shift chat needs more than 2 users on the shift.
MIN_SHIFT_CHAT_USERS = 3
# The "join chat" button shows from JOIN_BEFORE before the shift starts until
# JOIN_AFTER after it ends.
JOIN_BEFORE = timedelta(hours=1)
JOIN_AFTER = timedelta(hours=1)
# Nobody can post after the last covered shift ended this long ago.
CLOSE_AFTER = timedelta(hours=2)

# Mega chats open on Friday and Saturday (Monday is 0) from this hour,
# in the time zone of the project (`TIME_ZONE`).
MEGA_CHAT_WEEKDAYS = (4, 5)
MEGA_CHAT_FROM_HOUR = 18

MAX_CHAT_NAME_LENGTH = 128
MAX_MESSAGE_LENGTH = 2000

# `ping` writes at most this often per member. A member is online when the
# last write is newer than ONLINE_WITHIN.
PRESENCE_WRITE_INTERVAL = timedelta(seconds=15)
ONLINE_WITHIN = timedelta(seconds=45)
