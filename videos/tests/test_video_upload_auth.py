from datetime import timedelta

from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models.custom_user_models import CustomUser

MIN_MP4 = b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom'


class VideoUploadAuthTest(APITestCase):
    """
    Regresión: el access token de simplejwt expira (ACCESS_TOKEN_LIFETIME) y el
    front no reintentaba con el refresh token, así que una subida de video con
    un access token vencido devolvía 401 en /videos/ sin ninguna recuperación.
    Esta suite fija el contrato: un token vencido debe rechazarse, pero
    /api/token/refresh/ debe emitir uno nuevo que sí permita subir el video.
    """

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='uploader', email='uploader@example.com')
        self.user.set_password('testpassword123')
        self.user.save()
        self.url = reverse('video_list_create')

    def _upload_payload(self):
        return {
            'video_file': SimpleUploadedFile('clip.mp4', MIN_MP4, content_type='video/mp4'),
            'description': 'test',
            'tags': 't',
            'music': '',
        }

    def test_expired_access_token_is_rejected(self):
        refresh = RefreshToken.for_user(self.user)
        access = refresh.access_token
        access.set_exp(lifetime=timedelta(seconds=-1))

        response = self.client.post(
            self.url, self._upload_payload(), format='multipart',
            HTTP_AUTHORIZATION=f'Bearer {access}',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refreshed_token_can_upload_after_expiry(self):
        refresh = RefreshToken.for_user(self.user)
        refresh_url = reverse('token_refresh')

        refreshed = self.client.post(refresh_url, {'refresh': str(refresh)})
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        new_access = refreshed.data['access']

        response = self.client.post(
            self.url, self._upload_payload(), format='multipart',
            HTTP_AUTHORIZATION=f'Bearer {new_access}',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_anonymous_get_feed_is_not_blocked(self):
        """GET /videos/ es de lectura pública (IsAuthenticatedOrReadOnly)."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
