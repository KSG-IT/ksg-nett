from django.test import TestCase

from users.models import User


class LoginViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        user = User(username='user')
        user.set_password('password')
        user.save()

    def test_plain_user_login(self):
        response = self.client.post('/login/', {
            'username': 'user',
            'password': 'password'
        })

        self.assertEqual(response.status_code, 302)
        cookies = list(map(lambda x: x[0], response.client.cookies.items()))
        self.assertIn('sessionid', cookies)

