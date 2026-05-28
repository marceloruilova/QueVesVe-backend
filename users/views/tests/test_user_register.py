from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models.custom_user_models import CustomUser


class RegisterUserAPIViewTest(APITestCase):
    url = reverse('register_user')

    def setUp(self):
        self.valid_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'Testpass1',
            'bio': 'This is a bio'
        }
        self.invalid_data = {
            'username': '',
            'email': 'newuser@example.com',
            'password': 'Testpass1',
            'bio': 'This is a bio'
        }

    def test_user_registration_with_valid_data(self):
        response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CustomUser.objects.count(), 1)
        self.assertEqual(CustomUser.objects.get().username, 'newuser')

    def test_user_receives_token_upon_registration(self):
        response = self.client.post(self.url, self.valid_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('refresh', response.data)
        self.assertIn('access', response.data)

    def test_user_registration_with_invalid_data(self):
        response = self.client.post(self.url, self.invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_registration_duplicate_username(self):
        self.client.post(self.url, self.valid_data)
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_rejects_short_password(self):
        data = {**self.valid_data, 'password': 'Ab1'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_registration_rejects_password_without_uppercase(self):
        data = {**self.valid_data, 'password': 'testpass1'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_registration_rejects_password_without_number(self):
        data = {**self.valid_data, 'password': 'Testpassword'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_registration_rejects_password_without_lowercase(self):
        data = {**self.valid_data, 'password': 'TESTPASS1'}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
