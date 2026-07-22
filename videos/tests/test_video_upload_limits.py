from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models.custom_user_models import CustomUser
from videos.models import Video

MIN_MP4 = b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom'


class VideoUploadLimitsTest(TestCase):
    """
    Regresión: comprimir/validar duración y cuota antes de guardar el Video,
    para que un usuario no pueda subir contenido más largo que el límite ni
    ocupar más espacio del permitido.
    """

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='uploader2', email='uploader2@example.com')
        self.user.set_password('testpassword123')
        self.user.save()
        self.url = reverse('video_list_create')
        self.quota_url = reverse('video_quota')
        self.client = APIClient()
        access = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

    def _upload_payload(self, client_compressed=None):
        payload = {
            'video_file': SimpleUploadedFile('clip.mp4', MIN_MP4, content_type='video/mp4'),
            'description': 'test',
            'tags': 't',
            'music': '',
        }
        if client_compressed is not None:
            payload['client_compressed'] = client_compressed
        return payload

    @patch('videos.views.get_duration_seconds')
    def test_duration_exceeded_is_rejected(self, mock_duration):
        mock_duration.return_value = 90.0

        response = self.client.post(self.url, self._upload_payload(), format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'duration_exceeded')
        self.assertEqual(Video.objects.count(), 0)

    @patch('videos.views.get_duration_seconds')
    def test_duration_within_limit_is_accepted(self, mock_duration):
        mock_duration.return_value = 45.0

        response = self.client.post(self.url, self._upload_payload(), format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        video = Video.objects.get()
        self.assertEqual(video.duration_seconds, 45.0)
        self.assertEqual(video.file_size, len(MIN_MP4))

    @override_settings(UGC_STORAGE_QUOTA_BYTES=10)
    def test_quota_exceeded_is_rejected(self):
        response = self.client.post(self.url, self._upload_payload(), format='multipart')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'quota_exceeded')
        self.assertEqual(Video.objects.count(), 0)

    def test_quota_only_counts_ugc_videos(self):
        Video.objects.create(
            user=self.user, description='catalog', source_type='pexels',
            file_size=999_999_999,
        )

        response = self.client.post(self.url, self._upload_payload(), format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('videos.views.compress_video')
    def test_server_compresses_when_client_did_not(self, mock_compress):
        mock_compress.return_value = False

        response = self.client.post(
            self.url, self._upload_payload(client_compressed='false'), format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_compress.assert_called_once()

    @patch('videos.views.compress_video')
    def test_server_skips_compression_when_client_already_did(self, mock_compress):
        response = self.client.post(
            self.url, self._upload_payload(client_compressed='true'), format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_compress.assert_not_called()

    def test_quota_endpoint_reflects_usage(self):
        Video.objects.create(
            user=self.user, description='mine', source_type='ugc', file_size=1000,
        )
        Video.objects.create(
            user=self.user, description='catalog', source_type='pexels', file_size=999_999,
        )

        response = self.client.get(self.quota_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['used_bytes'], 1000)
        self.assertIn('limit_bytes', response.data)
        self.assertIn('remaining_bytes', response.data)

    def test_quota_endpoint_requires_auth(self):
        anon_client = APIClient()
        response = anon_client.get(self.quota_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
