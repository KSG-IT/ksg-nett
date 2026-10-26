"""
The number on the app icon: everything that waits for the user. Add a new
source as one more line in badge_count. The SPA shows this number, and a
push can carry it later.
"""

from django.conf import settings

from chat.utils import total_unread
from common.util import check_feature_flag


def badge_count(user):
    count = 0
    if check_feature_flag(settings.CHAT_FEATURE_FLAG, fail_silently=True):
        count += total_unread(user)
    return count
