from django.contrib.auth.models import User
from django.test import TestCase


# Create your tests here.
class TokenTest(TestCase):
    def test_create_user_should_generate_token(self):
        user = User(
            username='User 1'
        )
        user.save()
        self.assertIsNotNone(user.auth_token)
        self.assertIsInstance(user.auth_token.key, str)
