from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from users.models.custom_user_models import CustomUser
from videos.models import ContentImportLog, Video


class CleanupStorageCommandTest(TestCase):
    """
    cleanup_storage borra primero el catálogo propio (Pexels/Pixabay/Archive,
    del más antiguo al más nuevo) cuando su peso en DB (Video.file_size) supera
    --budget-bytes, y nunca toca contenido de usuarios (UGC). El peso se mide en
    la DB (no en disco local) para funcionar igual con storage local o R2.
    """

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='owner', email='owner@example.com', password='pass123')

    def _make_video(self, source_type, days_old=0, external_id='', file_size=1000):
        video = Video.objects.create(
            user=self.user,
            description=f'{source_type} video',
            tags='',
            music='',
            source_type=source_type,
            external_id=external_id,
            file_size=file_size,
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

    def test_target_must_be_below_budget(self):
        with self.assertRaises(CommandError):
            call_command('cleanup_storage', budget_bytes=1000, target_bytes=2000)

    def test_below_budget_does_nothing(self):
        self._make_video('pexels', days_old=5, file_size=1000)

        self._run(budget_bytes=10_000, target_bytes=8_000)

        self.assertEqual(Video.objects.count(), 1)

    def test_deletes_non_ugc_oldest_first_until_target(self):
        oldest = self._make_video('pexels', days_old=10, external_id='pexels_old', file_size=4000)
        middle = self._make_video('archive', days_old=5, external_id='archive_mid', file_size=4000)
        newest = self._make_video('pixabay', days_old=1, external_id='pixabay_new', file_size=4000)
        # total = 12000, budget 10000, target 5000 -> borra los dos mas viejos (8000),
        # queda en 4000 (<=5000), no llega a borrar el tercero.

        self._run(budget_bytes=10_000, target_bytes=5_000)

        remaining = set(Video.objects.values_list('external_id', flat=True))
        self.assertNotIn(oldest.external_id, remaining)
        self.assertNotIn(middle.external_id, remaining)
        self.assertIn(newest.external_id, remaining)

    def test_never_deletes_ugc(self):
        # El peso del catálogo se mide solo sobre fuentes no-UGC, así que con
        # únicamente un video UGC en la DB el catálogo pesa 0 -- forzamos budget=0
        # para que igual dispare el intento de limpieza y confirmar que no hay
        # candidatos no-UGC para borrar (el UGC nunca se toca).
        ugc_video = self._make_video('ugc', days_old=30, file_size=999_999)

        output = self._run(budget_bytes=0, target_bytes=-1, limit=10)

        self.assertTrue(Video.objects.filter(pk=ugc_video.pk).exists())
        self.assertIn('UGC', output)

    def test_respects_limit(self):
        for i in range(5):
            self._make_video('pexels', days_old=10 - i, external_id=f'pexels_{i}', file_size=1000)

        self._run(budget_bytes=1000, target_bytes=500, limit=2)

        self.assertEqual(Video.objects.filter(source_type='pexels').count(), 3)

    def test_dry_run_deletes_nothing(self):
        self._make_video('archive', days_old=5, external_id='archive_1', file_size=5000)

        output = self._run(budget_bytes=1000, target_bytes=500, dry_run=True)

        self.assertEqual(Video.objects.count(), 1)
        self.assertIn('DRY RUN', output)
        self.assertFalse(ContentImportLog.objects.filter(action='delete').exists())

    def test_deletion_is_logged_for_archive_source(self):
        # regresión: la señal de borrado sólo cubría pexels/pixabay, no archive
        self._make_video('archive', days_old=5, external_id='archive_log_test', file_size=5000)

        self._run(budget_bytes=1000, target_bytes=500)

        log = ContentImportLog.objects.filter(
            action='delete', external_id='archive_log_test'
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.source_type, 'archive')
