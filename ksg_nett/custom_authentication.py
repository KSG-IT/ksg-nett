from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()


class UsernameOrEmailOrCardNumberAuthenticationBackend(ModelBackend):
    """
    Enables authenticating through either username or email
    """

    # noinspection PyPep8Naming
    def authenticate(self, _request, username=None, password=None, **_kwargs):
        try:
            user = User.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username) | Q(bank_account__card_uuid=username))
        except User.DoesNotExist:
            return None

        return user if self.user_can_authenticate(user) and user.check_password(password) else None


class CardNumberAuthentication(BaseAuthentication):
    """
    Enables authenticating through only a card number.
    This is used for starting Soci session by scanning a card.
    """

    def authenticate(self, request):
        """
        "To implement a custom authentication scheme, subclass BaseAuthentication and override the
        .authenticate(self, request) method. The method should return a two-tuple of (user, auth) if authentication
        succeeds, or None otherwise."
        (source: https://www.django-rest-framework.org/api-guide/authentication/#custom-authentication)
        """

        try:
            user = User.objects.get(bank_account__card_uuid=request.data.get('card_uuid'))
        except User.DoesNotExist:
            raise AuthenticationFailed

        return user, None
