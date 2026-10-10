from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.utils import timezone

from login.middleware import JwtProviderMiddleware
from users.models import User
from users.tests.factories import UserFactory
from ksg_nett.settings import AUTH_JWT_METHOD, AUTH_JWT_SECRET
import jwt
from unittest import mock


class TestJwtProviderMiddleware(TestCase):
    def setUp(self) -> None:
        self.user = UserFactory.create()
        token = jwt.encode(
            {"id": self.user.pk}, AUTH_JWT_SECRET, algorithm=AUTH_JWT_METHOD
        )
        self.request = RequestFactory().get(
            "/graphql/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.middleware = JwtProviderMiddleware(lambda request: HttpResponse())

    def test__valid_token__updates_last_login(self):
        before = timezone.now()
        self.middleware(self.request)
        self.user.refresh_from_db()
        self.assertGreaterEqual(self.user.last_login, before)

    def test__valid_token__does_not_overwrite_other_columns(self):
        """A parallel request changes the user after the middleware loaded it."""
        real_now = timezone.now

        def now_after_parallel_write():
            User.objects.filter(pk=self.user.pk).update(first_name="Changed")
            return real_now()

        with mock.patch(
            "login.middleware.timezone.now", side_effect=now_after_parallel_write
        ):
            self.middleware(self.request)

        self.user.refresh_from_db()
        self.assertEqual("Changed", self.user.first_name)
