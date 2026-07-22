import shutil

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from videos.models import Video

# Prioridad de borrado: contenido propio (catálogo licenciado) antes que UGC.
# Los videos subidos por usuarios reales ('ugc') nunca se tocan acá --
# cuando exista un sistema de prioridades para UGC, este comando deberá
# extenderse para considerarlo.
NON_UGC_SOURCES = ['pexels', 'pixabay', 'archive']


class Command(BaseCommand):
    help = (
        'Limpieza selectiva de storage: si el uso de disco de MEDIA_ROOT supera '
        '--threshold, borra videos del catalogo propio (Pexels/Pixabay/Archive), '
        'del mas antiguo al mas nuevo, hasta bajar de --target. Nunca borra '
        'contenido subido por usuarios (UGC).\n\n'
        'Pensado para correr por cron/scheduler periodicamente.\n\n'
        'Ejemplos:\n'
        '  python manage.py cleanup_storage --dry-run\n'
        '  python manage.py cleanup_storage --threshold 90 --target 80\n'
        '  python manage.py cleanup_storage --limit 50\n'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=float,
            default=90.0,
            metavar='PCT',
            help='%% de uso de disco que dispara la limpieza (default: 90)',
        )
        parser.add_argument(
            '--target',
            type=float,
            default=80.0,
            metavar='PCT',
            help='%% de uso de disco al que se intenta bajar (default: 80)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=500,
            metavar='N',
            help='Maximo de videos a borrar en una sola corrida (default: 500)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra que borraria sin borrar nada',
        )

    def handle(self, *args, **options):
        threshold = options['threshold']
        target = options['target']
        limit = options['limit']
        dry_run = options['dry_run']

        if target >= threshold:
            raise CommandError('--target debe ser menor que --threshold')

        used_pct = self._disk_used_pct()
        self.stdout.write(f'Uso de disco actual en MEDIA_ROOT: {used_pct:.1f}%')

        if used_pct < threshold:
            self.stdout.write(self.style.SUCCESS(
                f'Por debajo del umbral ({threshold}%%) -- no se requiere limpieza.'
            ))
            return

        self.stdout.write(self.style.WARNING(
            f'Uso de disco ({used_pct:.1f}%%) supera el umbral ({threshold}%%) -- '
            f'iniciando limpieza selectiva (objetivo: {target}%%).'
        ))

        candidate_ids = list(
            Video.objects.filter(source_type__in=NON_UGC_SOURCES)
            .order_by('created_at')
            .values_list('id', flat=True)
        )

        deleted = 0
        freed_bytes = 0
        prefix = '[DRY RUN] ' if dry_run else ''

        for video_id in candidate_ids:
            if deleted >= limit:
                self.stdout.write(self.style.WARNING(
                    f'Limite de {limit} eliminaciones por corrida alcanzado.'
                ))
                break

            if self._disk_used_pct() <= target:
                break

            video = Video.objects.filter(id=video_id).first()
            if not video:
                continue

            size = self._file_size(video)

            self.stdout.write(
                f'  {prefix}[-] {video.external_id or video.id} '
                f'({video.source_type}, {video.created_at:%Y-%m-%d}, {self._human(size)})'
            )
            if not dry_run:
                video.delete()  # dispara post_delete signal -> ContentImportLog

            deleted += 1
            freed_bytes += size

        final_pct = self._disk_used_pct()

        if deleted == 0:
            self.stdout.write(self.style.WARNING(
                f'{prefix}No habia videos propios (Pexels/Pixabay/Archive) para eliminar. '
                'El uso de disco sigue por encima del umbral y el resto es contenido de '
                'usuarios (UGC) -- no se toca automaticamente. Requiere intervencion manual '
                'o una politica de prioridades para UGC.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'{prefix}Listo -- {deleted} videos eliminados, '
                f'~{self._human(freed_bytes)} liberados. Uso de disco ahora: {final_pct:.1f}%.'
            ))

    # ------------------------------------------------------------------

    def _disk_used_pct(self):
        usage = shutil.disk_usage(settings.MEDIA_ROOT)
        return usage.used / usage.total * 100

    def _file_size(self, video):
        try:
            if video.video_file and video.video_file.storage.exists(video.video_file.name):
                return video.video_file.size
        except (ValueError, OSError):
            pass
        return 0

    @staticmethod
    def _human(num_bytes):
        value = float(num_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if value < 1024:
                return f'{value:.1f}{unit}'
            value /= 1024
        return f'{value:.1f}PB'
