from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum

from videos.models import Video

# Prioridad de borrado: contenido propio (catálogo licenciado) antes que UGC.
# Los videos subidos por usuarios reales ('ugc') nunca se tocan acá --
# cuando exista un sistema de prioridades para UGC, este comando deberá
# extenderse para considerarlo.
NON_UGC_SOURCES = ['pexels', 'pixabay', 'archive']


class Command(BaseCommand):
    help = (
        'Limpieza selectiva de storage: si el peso total del catálogo propio '
        '(Pexels/Pixabay/Archive, medido en la DB vía Video.file_size) supera '
        '--budget-bytes, borra videos del catalogo propio, del mas antiguo al '
        'mas nuevo, hasta bajar de --target-bytes. Nunca borra contenido subido '
        'por usuarios (UGC).\n\n'
        'Mide el peso del catálogo en la DB (no en disco local) para funcionar '
        'igual sea el storage filesystem local o Cloudflare R2.\n\n'
        'Pensado para correr por cron/scheduler periodicamente.\n\n'
        'Ejemplos:\n'
        '  python manage.py cleanup_storage --dry-run\n'
        '  python manage.py cleanup_storage --budget-bytes 5000000000 --target-bytes 4000000000\n'
        '  python manage.py cleanup_storage --limit 50\n'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--budget-bytes',
            type=int,
            default=None,
            metavar='BYTES',
            help='Peso del catalogo que dispara la limpieza (default: CATALOG_STORAGE_BUDGET_BYTES)',
        )
        parser.add_argument(
            '--target-bytes',
            type=int,
            default=None,
            metavar='BYTES',
            help='Peso al que se intenta bajar el catalogo (default: 80%% del budget)',
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
        budget = options['budget_bytes']
        if budget is None:
            budget = settings.CATALOG_STORAGE_BUDGET_BYTES
        target = options['target_bytes']
        if target is None:
            target = int(budget * 0.8)
        limit = options['limit']
        dry_run = options['dry_run']

        if target >= budget:
            raise CommandError('--target-bytes debe ser menor que --budget-bytes')

        used_bytes = self._catalog_used_bytes()
        self.stdout.write(f'Peso actual del catálogo propio: {self._human(used_bytes)}')

        if used_bytes < budget:
            self.stdout.write(self.style.SUCCESS(
                f'Por debajo del presupuesto ({self._human(budget)}) -- no se requiere limpieza.'
            ))
            return

        self.stdout.write(self.style.WARNING(
            f'Peso del catálogo ({self._human(used_bytes)}) supera el presupuesto '
            f'({self._human(budget)}) -- iniciando limpieza selectiva '
            f'(objetivo: {self._human(target)}).'
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

            if used_bytes <= target:
                break

            video = Video.objects.filter(id=video_id).first()
            if not video:
                continue

            size = video.file_size

            self.stdout.write(
                f'  {prefix}[-] {video.external_id or video.id} '
                f'({video.source_type}, {video.created_at:%Y-%m-%d}, {self._human(size)})'
            )
            if not dry_run:
                video.delete()  # dispara post_delete signal -> ContentImportLog

            deleted += 1
            freed_bytes += size
            used_bytes -= size

        if deleted == 0:
            self.stdout.write(self.style.WARNING(
                f'{prefix}No habia videos propios (Pexels/Pixabay/Archive) para eliminar. '
                'El catálogo sigue por encima del presupuesto y el resto es contenido de '
                'usuarios (UGC) -- no se toca automaticamente. Requiere intervencion manual '
                'o una politica de prioridades para UGC.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'{prefix}Listo -- {deleted} videos eliminados, '
                f'~{self._human(freed_bytes)} liberados. Peso del catálogo ahora: '
                f'{self._human(used_bytes)}.'
            ))

    # ------------------------------------------------------------------

    def _catalog_used_bytes(self):
        return Video.objects.filter(source_type__in=NON_UGC_SOURCES).aggregate(
            total=Sum('file_size')
        )['total'] or 0

    @staticmethod
    def _human(num_bytes):
        value = float(num_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if value < 1024:
                return f'{value:.1f}{unit}'
            value /= 1024
        return f'{value:.1f}PB'
