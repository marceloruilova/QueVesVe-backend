import shutil
from io import StringIO
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase

from users.models.custom_user_models import CustomUser
from videos.models import Video


class StorageToggleTest(TestCase):
    """Guarda de regresión: bajo el test runner siempre debe usarse FileSystemStorage,
    sin importar el valor de USE_R2_STORAGE en el entorno, para no depender de
    credenciales reales de R2 en dev/CI."""

    def test_filesystem_storage_used_under_tests(self):
        self.assertFalse(settings.USE_R2_STORAGE)
        self.assertEqual(
            settings.STORAGES['default']['BACKEND'],
            'django.core.files.storage.FileSystemStorage',
        )


class MigrateMediaToR2Test(TestCase):
    """
    migrate_media_to_r2 copia archivos del filesystem local a R2 preservando el
    nombre. Como no hay bucket real disponible en tests, se mockea el storage de
    destino y se verifica la lógica del comando (skip si ya existe, no sube en
    dry-run, preserva el nombre exacto al subir).
    """

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='migrator', email='migrator@example.com', password='pass123')

    def tearDown(self):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def _make_video(self):
        return Video.objects.create(
            user=self.user, description='t', tags='', music='',
            video_file=SimpleUploadedFile('clip.mp4', b'hello world', content_type='video/mp4'),
        )

    @patch('videos.management.commands.migrate_media_to_r2.Command._build_dest_storage')
    def test_dry_run_does_not_upload(self, mock_build_dest):
        dest = MagicMock()
        dest.exists.return_value = False
        mock_build_dest.return_value = dest
        self._make_video()

        out = StringIO()
        call_command('migrate_media_to_r2', dry_run=True, only='videos', stdout=out)

        dest._save.assert_not_called()
        self.assertIn('migrados', out.getvalue())

    @patch('videos.management.commands.migrate_media_to_r2.Command._build_dest_storage')
    def test_skips_objects_already_in_destination(self, mock_build_dest):
        dest = MagicMock()
        dest.exists.return_value = True
        mock_build_dest.return_value = dest
        self._make_video()

        call_command('migrate_media_to_r2', only='videos', stdout=StringIO())

        dest._save.assert_not_called()

    @patch('videos.management.commands.migrate_media_to_r2.Command._build_dest_storage')
    def test_uploads_missing_objects_preserving_name(self, mock_build_dest):
        dest = MagicMock()
        dest.exists.return_value = False
        mock_build_dest.return_value = dest
        video = self._make_video()
        original_name = video.video_file.name

        call_command('migrate_media_to_r2', only='videos', stdout=StringIO())

        dest._save.assert_called_once()
        called_name = dest._save.call_args[0][0]
        self.assertEqual(called_name, original_name)

    @patch('videos.management.commands.migrate_media_to_r2.Command._build_dest_storage')
    def test_only_filters_to_a_single_group(self, mock_build_dest):
        dest = MagicMock()
        dest.exists.return_value = False
        mock_build_dest.return_value = dest
        CustomUser.objects.create_user(
            username='other', email='other@example.com', password='pass123',
            profile_picture=SimpleUploadedFile('pic.jpg', b'img', content_type='image/jpeg'),
        )
        self._make_video()

        call_command('migrate_media_to_r2', only='profile_pictures', stdout=StringIO())

        dest._save.assert_called_once()
        called_name = dest._save.call_args[0][0]
        self.assertTrue(called_name.startswith('profile_pictures/'))
