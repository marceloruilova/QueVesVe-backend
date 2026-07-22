from django.core.management.base import BaseCommand

from videos.media_utils import get_duration_seconds
from videos.models import Video


class Command(BaseCommand):
    help = (
        'Poblá file_size y duration_seconds de videos ya subidos antes de que estos '
        'campos existieran (necesario para que la cuota de almacenamiento por usuario '
        'sea correcta). Por default solo procesa videos con file_size=0 (idempotente).\n\n'
        'Ejemplos:\n'
        '  python manage.py backfill_video_metadata --dry-run\n'
        '  python manage.py backfill_video_metadata --limit 200\n'
        '  python manage.py backfill_video_metadata --force\n'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            metavar='N',
            help='Maximo de videos a procesar en esta corrida (default: todos)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra que se actualizaria sin guardar nada',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Reprocesa tambien videos que ya tienen file_size distinto de 0',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        dry_run = options['dry_run']
        force = options['force']

        qs = Video.objects.all() if force else Video.objects.filter(file_size=0)
        qs = qs.order_by('id')
        if limit:
            qs = qs[:limit]

        prefix = '[DRY RUN] ' if dry_run else ''
        processed = 0
        total_bytes = 0

        for video in qs:
            size = self._file_size(video)
            duration = self._duration(video)

            self.stdout.write(
                f'  {prefix}[{video.id}] {video.video_file.name} -> '
                f'{self._human(size)}, {self._fmt_duration(duration)}'
            )

            if not dry_run:
                video.file_size = size
                video.duration_seconds = duration
                video.save(update_fields=['file_size', 'duration_seconds'])

            processed += 1
            total_bytes += size

        self.stdout.write(self.style.SUCCESS(
            f'{prefix}Listo -- {processed} videos procesados, '
            f'~{self._human(total_bytes)} contabilizados.'
        ))

    # ------------------------------------------------------------------

    def _file_size(self, video):
        try:
            if video.video_file and video.video_file.storage.exists(video.video_file.name):
                return video.video_file.size
        except (ValueError, OSError):
            pass
        return 0

    def _duration(self, video):
        try:
            path = video.video_file.path
        except (ValueError, NotImplementedError):
            return None
        return get_duration_seconds(path)

    @staticmethod
    def _fmt_duration(duration):
        if duration is None:
            return 'duración desconocida'
        mins, secs = divmod(int(duration), 60)
        return f'{mins}:{secs:02d} min'

    @staticmethod
    def _human(num_bytes):
        value = float(num_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if value < 1024:
                return f'{value:.1f}{unit}'
            value /= 1024
        return f'{value:.1f}PB'
