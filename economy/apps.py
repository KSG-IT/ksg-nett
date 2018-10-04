from django.apps import AppConfig


class EconomyConfig(AppConfig):
    name = 'economy'

    # noinspection PyUnresolvedReferences
    def ready(self):
        import economy.signals
