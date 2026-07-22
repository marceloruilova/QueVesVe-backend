from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from users.models.custom_user_models import CustomUser
from videos.models import ContentImportLog, Video


def stepped_pct(start, step, floor=0.0):
    """Devuelve valores decrecientes en cada llamada, simulando espacio liberado."""
    state = {'val': start}

    def _side_effect():
        val = state['val']
        state['val'] = max(floor, val - step)
        return val

    return _side_effect


class CleanupStorageCommandTest(TestCase):
    """
    cleanup_storage borra primero el catálogo propio (Pexels/Pixabay/Archive,
    del más antiguo al más nuevo) cuando el disco supera --threshold, y nunca
    toca contenido de usuarios (UGC) porque todavía no existe un sistema de
    prioridades para UGC.
    """

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='owner', email='owner@example.com', password='pass123')

    def _make_video(self, source_type, days_old=0, external_id=''):
        video = Video.objects.create(
            user=self.user,
            description=f'{source_type} video',
            tags='',
            music='',
            source_type=source_type,
            external_id=external_id,
        )
        if days_old:
            Video.objects.filter(pk=video.pk).update(
                created_at=timezone.now() - timedelta(days=days_old)
            )
        return video

    def _run(self, **options):
        out = StringIO()
        call_command('cleanup_storage', stdout=out, **options)
        return out.getvalue()

    # ------------------------------------------------------------------

    def test_target_must_be_below_threshold(self):
        with self.assertRaises(CommandError):
            call_command('cleanup_storage', threshold=80, target=90)

    @patch('videos.management.commands.cleanup_storage.Command._disk_used_pct')
    def test_below_threshold_does_nothing(self, mock_pct):
        mock_pct.return_value = 50.0
        self._make_video('pexels', days_old=5)

        self._run(threshold=90, target=80)

        self.assertEqual(Video.objects.count(), 1)

    @patch('videos.management.commands.cleanup_storage.Command._disk_used_pct')
    def test_deletes_non_ugc_oldest_first_until_target(self, mock_pct):
        oldest = self._make_video('pexels', days_old=10, external_id='pexels_old')
        middle = self._make_video('archive', days_old=5, external_id='archive_mid')
        newest = self._make_video('pixabay', days_old=1, external_id='pixabay_new')

        # 95 (chequeo inicial) -> 89 -> 83 -> 77 (<=80, corta antes de borrar el 3ro)
        mock_pct.side_effect = stepped_pct(start=95.0, step=6.0)

        self._run(threshold=90, target=80)

        remaining = set(Video.objects.values_list('external_id', flat=True))
        self.assertNotIn(oldest.external_id, remaining)
        self.assertNotIn(middle.external_id, remaining)
        self.assertIn(newest.external_id, remaining)

    @patch('videos.management.commands.cleanup_storage.Command._disk_used_pct')
    def test_never_deletes_ugc(self, mock_pct):
        ugc_video = self._make_video('ugc', days_old=30)
        mock_pct.return_value = 99.0  # siempre por encima del umbral y del target

        output = self._run(threshold=90, target=80, limit=10)

        self.assertTrue(Video.objects.filter(pk=ugc_video.pk).exists())
        self.assertIn('UGC', output)

    @patch('videos.management.commands.cleanup_storage.Command._disk_used_pct')
    def test_respects_limit(self, mock_pct):
        for i in range(5):
            self._make_video('pexels', days_old=10 - i, external_id=f'pexels_{i}')
        mock_pct.return_value = 95.0  # nunca baja del target -> seguiría borrando sin el limit

        self._run(threshold=90, target=80, limit=2)

        self.assertEqual(Video.objects.filter(source_type='pexels').count(), 3)

    @patch('videos.management.commands.cleanup_storage.Command._disk_used_pct')
    def test_dry_run_deletes_nothing(self, mock_pct):
        self._make_video('archive', days_old=5, external_id='archive_1')
        mock_pct.return_value = 95.0

        output = self._run(threshold=90, target=80, dry_run=True)

        self.assertEqual(Video.objects.count(), 1)
        self.assertIn('DRY RUN', output)
        self.assertFalse(ContentImportLog.objects.filter(action='delete').exists())

    @patch('videos.management.commands.cleanup_storage.Command._disk_used_pct')
    def test_deletion_is_logged_for_archive_source(self, mock_pct):
        # regresión: la señal de borrado sólo cubría pexels/pixabay, no archive
        self._make_video('archive', days_old=5, external_id='archive_log_test')
        mock_pct.side_effect = stepped_pct(start=95.0, step=10.0)

        self._run(threshold=90, target=80)

        log = ContentImportLog.objects.filter(
            action='delete', external_id='archive_log_test'
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.source_type, 'archive')
