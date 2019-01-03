from django.apps import AppConfig


class ChatConfig(AppConfig):
    name = 'chat'

    def ready(self):
        # noinspection PyUnresolvedReferences
        import chat.redis
