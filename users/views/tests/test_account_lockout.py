from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from users.models.custom_user_models import CustomUser
from users.constants import ACCOUNT_LOCKED_ERROR


class AccountLockoutTest(APITestCase):
    """Confirma que django-axes bloquee la cuenta al llegar a AXES_FAILURE_LIMIT=5 fallos,
    incluso con la contraseña correcta después. Se deshabilita el LoginRateThrottle acá
    para poder mandar más de 5 requests en el mismo minuto y aislar el comportamiento de axes.

    Nota: axes marca como bloqueado el intento que hace que el conteo llegue al límite (el
    5to), no recién el siguiente — así que solo los primeros 4 fallos ven la respuesta normal
    de "credenciales incorrectas"."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='lockoutuser', email='lockout@example.com', password='CorrectPass1')
        self.url = reverse('login_user')

    @patch('quevesve_back.throttles.LoginRateThrottle.allow_request', return_value=True)
    def test_fifth_failed_attempt_locks_account(self, _mock_throttle):
        for _ in range(4):
            response = self.client.post(self.url, {
                'username': 'lockoutuser', 'password': 'wrongpassword',
            })
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(self.url, {
            'username': 'lockoutuser', 'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.json()['error'], ACCOUNT_LOCKED_ERROR)

        # Incluso con la contraseña correcta, sigue bloqueado durante el cooloff.
        response = self.client.post(self.url, {
            'username': 'lockoutuser', 'password': 'CorrectPass1',
        })
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_successful_login_is_not_affected_by_axes(self):
        response = self.client.post(self.url, {
            'username': 'lockoutuser', 'password': 'CorrectPass1',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
