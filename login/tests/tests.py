from django.test import TestCase

from users.tests.factories import UserFactory


class LoginViewTest(TestCase):

    @classmethod
    def setUp(self):
        user = UserFactory(username='user')
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

    def test_plain_user_logout(self):
        response = self.client.post('/login/', {
            'username': 'user',
            'password': 'password'
        })
        self.assertEqual(response.status_code, 302)
        cookies = list(map(lambda x: x[0], response.client.cookies.items()))
        self.assertIn('sessionid', cookies)
        response = self.client.post('/logout/')
        self.assertEqual(response.status_code, 302)
        cookies = {
            k: v.value for k, v in response.client.cookies.items()
        }
        self.assertEqual(cookies['sessionid'], '')

    def test_plain_user_logout_GET_should_logout(self):
        response = self.client.post('/login/', {
            'username': 'user',
            'password': 'password'
        })
        self.assertEqual(response.status_code, 302)
        cookies = list(map(lambda x: x[0], response.client.cookies.items()))
        self.assertIn('sessionid', cookies)
        response = self.client.get('/logout/')
        self.assertEqual(response.status_code, 302)
        cookies = {
            k: v.value for k, v in response.client.cookies.items()
        }
        self.assertEqual(cookies['sessionid'], '')
