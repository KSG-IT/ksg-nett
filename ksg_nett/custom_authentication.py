from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class UsernameOrEmailOrCardNumberAuthenticationBackend(ModelBackend):
    """
    Enables authenticating through either username, email or card number
    """

    # noinspection PyPep8Naming
    def authenticate(self, _request, username=None, password=None, **_kwargs):
        User = get_user_model()
        username = username.lower()
        try:
            user = User.objects.get(Q(username=username) | Q(email=username) | Q(bank_account__card_uuid=username))
        except User.DoesNotExist:
            return None

        return user if self.user_can_authenticate(user) and user.check_password(password) else None
