import datetime
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models.custom_user_models import CustomUser
from users.models.email_verification_token_model import EmailVerificationToken


def make_user(username='verifyuser', email='verify@example.com', password='Testpass1'):
    user = CustomUser.objects.create_user(username=username, email=email, password=password)
    return user


def auth_header(user):
    refresh = RefreshToken.for_user(user)
    return {'HTTP_AUTHORIZATION': f'Bearer {refresh.access_token}'}


REGISTER_URL = reverse('register_user')
RESEND_URL = reverse('resend_verification')
VALID_REG_DATA = {
    'username': 'newverifyuser',
    'email': 'newverify@example.com',
    'password': 'Testpass1',
}


class RegistrationEmailVerificationTest(APITestCase):

    @patch('users.views.user_register_view.send_verification_email')
    def test_registration_creates_verification_token(self, mock_send):
        self.client.post(REGISTER_URL, VALID_REG_DATA)
        user = CustomUser.objects.get(username='newverifyuser')
        self.assertTrue(EmailVerificationToken.objects.filter(user=user).exists())

    @patch('users.views.user_register_view.send_verification_email')
    def test_registration_response_includes_email_verified_false(self, mock_send):
        response = self.client.post(REGISTER_URL, VALID_REG_DATA)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['user']['email_verified'])

    @patch('users.views.user_register_view.send_verification_email')
    def test_email_sent_on_registration(self, mock_send):
        self.client.post(REGISTER_URL, VALID_REG_DATA)
        mock_send.assert_called_once()
        args = mock_send.call_args[0]
        self.assertEqual(args[0], VALID_REG_DATA['email'])
        self.assertEqual(args[1], VALID_REG_DATA['username'])


class VerifyEmailTokenTest(APITestCase):

    def setUp(self):
        self.user = make_user()
        self.token = EmailVerificationToken.objects.create(user=self.user)
        self.verify_url = reverse('verify_email', kwargs={'token': self.token.token})

    def test_verify_valid_token_returns_200_html(self):
        response = self.client.get(self.verify_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response['Content-Type'])

    def test_verify_valid_token_marks_user_verified(self):
        self.client.get(self.verify_url)
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)

    def test_verify_valid_token_deletes_token(self):
        self.client.get(self.verify_url)
        self.assertFalse(EmailVerificationToken.objects.filter(user=self.user).exists())

    def test_verify_invalid_token_returns_400(self):
        url = reverse('verify_email', kwargs={'token': '00000000-0000-0000-0000-000000000000'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_verify_expired_token_returns_410(self):
        self.token.created_at = timezone.now() - datetime.timedelta(hours=25)
        self.token.save()
        response = self.client.get(self.verify_url)
        self.assertEqual(response.status_code, 410)

    def test_verify_expired_token_does_not_verify_user(self):
        self.token.created_at = timezone.now() - datetime.timedelta(hours=25)
        self.token.save()
        self.client.get(self.verify_url)
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_verified)

    def test_verify_token_is_single_use(self):
        self.client.get(self.verify_url)
        response = self.client.get(self.verify_url)
        self.assertEqual(response.status_code, 400)


class ResendVerificationEmailTest(APITestCase):

    def setUp(self):
        self.user = make_user()

    def test_resend_requires_auth(self):
        response = self.client.post(RESEND_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('users.views.email_verification_view.send_verification_email')
    def test_resend_when_not_verified_returns_200(self, mock_send):
        response = self.client.post(RESEND_URL, **auth_header(self.user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('users.views.email_verification_view.send_verification_email')
    def test_resend_creates_new_token(self, mock_send):
        self.client.post(RESEND_URL, **auth_header(self.user))
        self.assertTrue(EmailVerificationToken.objects.filter(user=self.user).exists())

    @patch('users.views.email_verification_view.send_verification_email')
    def test_resend_when_already_verified_returns_200_with_message(self, mock_send):
        self.user.email_verified = True
        self.user.save()
        response = self.client.post(RESEND_URL, **auth_header(self.user))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('verificado', response.data['detail'])

    @patch('users.views.email_verification_view.send_verification_email')
    def test_resend_rate_limit_within_5_minutes(self, mock_send):
        self.client.post(RESEND_URL, **auth_header(self.user))
        response = self.client.post(RESEND_URL, **auth_header(self.user))
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @patch('users.views.email_verification_view.send_verification_email')
    def test_resend_replaces_old_token_after_5_minutes(self, mock_send):
        old_token = EmailVerificationToken.objects.create(user=self.user)
        old_token.created_at = timezone.now() - datetime.timedelta(minutes=6)
        old_token.save()
        old_uuid = old_token.token

        self.client.post(RESEND_URL, **auth_header(self.user))

        new_token = EmailVerificationToken.objects.get(user=self.user)
        self.assertNotEqual(new_token.token, old_uuid)
