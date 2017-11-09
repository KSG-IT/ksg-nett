from django.contrib.auth import login
from django.test import TestCase, Client
from users.models import User


# Create your tests here.
class InternalRouteTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        user = User(username='me', email='my@email.com')
        user.set_password('pw')
        user.save()

    def test_index_without_logging_in_should_redirect(self):
        response = self.client.get('/internal/')
        self.assertEqual(response.status_code, 302)

    def test_index_with_logging_in_should_not_redirect(self):
        client = Client()
        client.login(username='me', password='pw')
        response = client.get('/internal/')

        self.assertEqual(response.status_code, 200)
        parsed_content = response.content.decode()

        self.assertIn('<!DOCTYPE html>', parsed_content, 'Erroneous html declaration, expected html5')
        self.assertIn('<html', parsed_content)
