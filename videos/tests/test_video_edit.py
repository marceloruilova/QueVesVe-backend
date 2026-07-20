from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models.custom_user_models import CustomUser
from videos.models import Video


class VideoEditTest(APITestCase):
    """
    Regresión: un video publicado sin descripción/música no se podía editar
    después. PATCH /videos/<id>/ debe permitir que sólo quien lo subió
    actualice description/tags/music, sin exigir de nuevo el archivo de video.
    """

    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username='owner', email='owner@example.com', password='pass123')
        self.other = CustomUser.objects.create_user(
            username='other', email='other@example.com', password='pass123')
        self.video = Video.objects.create(
            user=self.owner,
            description='',
            tags='',
            music='',
        )
        self.url = reverse('video_detail', kwargs={'videoid': self.video.id})

    def _auth(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_owner_can_add_missing_description_and_music(self):
        self._auth(self.owner)
        response = self.client.patch(
            self.url, {'description': 'Ahora sí tiene descripción', 'music': 'Canción X'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.video.refresh_from_db()
        self.assertEqual(self.video.description, 'Ahora sí tiene descripción')
        self.assertEqual(self.video.music, 'Canción X')

    def test_owner_partial_update_leaves_other_fields_untouched(self):
        self.video.description = 'Original'
        self.video.tags = '#original'
        self.video.save()
        self._auth(self.owner)

        response = self.client.patch(self.url, {'music': 'Nueva canción'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.video.refresh_from_db()
        self.assertEqual(self.video.description, 'Original')
        self.assertEqual(self.video.tags, '#original')
        self.assertEqual(self.video.music, 'Nueva canción')

    def test_non_owner_cannot_edit(self):
        self._auth(self.other)
        response = self.client.patch(self.url, {'description': 'Hackeado'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.video.refresh_from_db()
        self.assertEqual(self.video.description, '')

    def test_anonymous_cannot_edit(self):
        response = self.client.patch(self.url, {'description': 'Anon'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cannot_edit_readonly_fields_via_patch(self):
        """user_id no debe poder cambiarse a través de este endpoint."""
        self._auth(self.owner)
        response = self.client.patch(
            self.url, {'description': 'ok', 'user_id': self.other.id}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.video.refresh_from_db()
        self.assertEqual(self.video.user_id, self.owner.id)
