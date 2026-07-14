from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models.custom_user_models import CustomUser
from videos.models import Video


class VideoFeedTest(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='videouser', email='video@example.com', password='pass123')
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        self.video = Video.objects.create(
            user=self.user,
            description='Test video',
            tags='test',
            music='test music',
        )

    def test_feed_includes_user_id(self):
        """GET /videos/ must include user_id so the frontend can navigate to the profile."""
        response = self.client.get(reverse('video_list_create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)
        first = response.data[0]
        self.assertIn('user_id', first)
        self.assertEqual(first['user_id'], self.user.id)
        self.assertIn('username', first)

    def test_feed_filter_by_user_id(self):
        """GET /videos/?user_id=<id> returns only that user's videos."""
        other = CustomUser.objects.create_user(
            username='other', email='other2@example.com', password='pass123')
        Video.objects.create(user=other, description='Other video', tags='', music='')

        response = self.client.get(f"{reverse('video_list_create')}?user_id={self.user.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(all(v['user_id'] == self.user.id for v in response.data))
