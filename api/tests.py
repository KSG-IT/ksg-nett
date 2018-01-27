from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from commissions.models import Commission
from users.models import User


# ===============================
# COMMISSIONS
# ===============================

class ListCommissionsViewTest(APITestCase):
    def setUp(self):
        self.url = reverse('list-commissions')
        self.client = APIClient()
        self.user = User.objects.create(username='test')
        self.client.force_authenticate(user=self.user)
        self.commission = Commission.objects.create(name='Super awesome verv')
        self.user.commission = self.commission
        self.user.save()

    def test_get_commissions__ok(self):
        response = self.client.get(self.url)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)
        self.assertEquals(response.data[0]['name'], 'Super awesome verv')
        self.assertEquals(self.commission.holders.first(), self.user)


class CreateCommissionViewTest(APITestCase):
    def setUp(self):
        self.url = reverse('create-commission')
        self.client = APIClient()
        self.client.force_authenticate(User.objects.create(username='test'))

    def test_create_commission__correct_info__created(self):
        data = {'name': 'Super awesome verv'}

        response = self.client.post(self.url, data, format='json')

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_create_commission__duplicate_commission__conflict(self):
        Commission.objects.create(name='Super awesome verv')
        data = {'name': 'Super awesome verv'}

        response = self.client.post(self.url, data, format='json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_commission__incorrect_info__bad_request(self):
        data = {'bad_attribute': 'lolwut'}

        response = self.client.post(self.url, data, format='json')

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)


class UpdateCommissionViewTest(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(User.objects.create(username='test'))
        self.commission = Commission.objects.create(name='Super awesome verv')
        self.url = reverse('update-commission', args=[self.commission.id])

    def test_update_commission__correct_info__created(self):
        data = {'name': 'Even more super awesomer verv'}

        response = self.client.patch(self.url, data, format='json')

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_update_commission__incorrect_info__not_found(self):
        data = {'name': 'Even more super awesomer verv'}
        self.url = reverse('update-commission', args=[self.commission.id + 1])

        response = self.client.patch(self.url, data, format='json')

        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)


class DeleteCommissionViewTest(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(User.objects.create(username='test'))
        self.commission = Commission.objects.create(name='Super awesome verv')
        self.url = reverse('delete-commission', args=[self.commission.id])

    def test_delete_commission__correct_info__deleted(self):
        response = self.client.delete(self.url)

        self.assertEquals(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_update_commission__incorrect_info__not_found(self):
        self.url = reverse('delete-commission', args=[self.commission.id + 1])

        response = self.client.delete(self.url)

        self.assertEquals(response.status_code, status.HTTP_404_NOT_FOUND)


# ===============================
# USERS
# ===============================

class TokenTest(TestCase):
    def test_create_user_should_generate_token(self):
        user = User(
            username='User 1'
        )
        user.save()
        self.assertIsNotNone(user.auth_token)
        self.assertIsInstance(user.auth_token.key, str)


class UserAPITest(TestCase):
    def test_has_contact(self):
        self.assertEqual(self.client.get('/api/users/').status_code, 200)
