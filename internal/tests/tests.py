from django.test import TestCase, Client

from users.tests.factories import UserFactory


class InternalRouteTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        user = UserFactory(username='me')
        user.set_password('pw')
        user.save()

    def test_index_without_logging_in_should_redirect(self):
        response = self.client.get('/internal/')
        self.assertEqual(response.status_code, 302)

    def test_index__logged_in__should_render_frontpage(self):
        client = Client()
        client.login(username='me', password='pw')
        response = client.get('/internal/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'internal/base.html')
        self.assertTemplateUsed(response, 'internal/frontpage.html')
        self.assertTemplateUsed(response, 'internal/header.html')

        # Check that some key context variables are passed along.
        self.assertIsNotNone(response.context.get('last_summaries'))
        self.assertIsNotNone(response.context.get('last_quotes'))

    def test_not_found__non_matching_url__catches_the_request(self):
        client = Client()
        client.login(username='me', password='pw')
        response = client.get('/internal/this-does-not-match-anything')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'internal/not_found.html')
