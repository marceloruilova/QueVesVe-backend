from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count

from videos.models import ContentImportLog, Video


class Command(BaseCommand):
    help = (
        'Muestra el reporte diario de contenido importado/eliminado.\n\n'
        'Ejemplos:\n'
        '  python manage.py content_report               # hoy\n'
        '  python manage.py content_report --date 2026-07-01\n'
        '  python manage.py content_report --days 7      # últimos 7 días\n'
        '  python manage.py content_report --summary     # resumen global de la DB\n'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            metavar='YYYY-MM-DD',
            help='Fecha específica (default: hoy)',
        )
        parser.add_argument(
            '--days',
            type=int,
            metavar='N',
            help='Muestra los últimos N días en vez de un solo día',
        )
        parser.add_argument(
            '--summary',
            action='store_true',
            help='Resumen global del estado actual de la DB (no filtrado por fecha)',
        )

    def handle(self, *args, **options):
        if options['summary']:
            self._print_db_summary()
            return

        if options['days']:
            end = date.today()
            start = end - timedelta(days=options['days'] - 1)
            self._print_range(start, end)
        else:
            target = date.today()
            if options['date']:
                try:
                    target = date.fromisoformat(options['date'])
                except ValueError:
                    self.stderr.write(f'Fecha inválida: {options["date"]} — usá YYYY-MM-DD')
                    return
            self._print_day(target)

    # ------------------------------------------------------------------

    def _print_day(self, target_date):
        self.stdout.write(f'\n{"="*55}')
        self.stdout.write(f'  REPORTE DE CONTENIDO — {target_date:%d/%m/%Y}')
        self.stdout.write(f'{"="*55}')

        imports = ContentImportLog.objects.filter(
            action='import', created_at__date=target_date
        )
        deletes = ContentImportLog.objects.filter(
            action='delete', created_at__date=target_date
        )

        self._print_imports(imports)
        self._print_deletes(deletes)

        if not imports.exists() and not deletes.exists():
            self.stdout.write('  (sin actividad este día)\n')

    def _print_range(self, start, end):
        self.stdout.write(f'\n{"="*55}')
        self.stdout.write(f'  REPORTE DE CONTENIDO — {start:%d/%m/%Y} -> {end:%d/%m/%Y}')
        self.stdout.write(f'{"="*55}')

        current = start
        while current <= end:
            imports_count = ContentImportLog.objects.filter(
                action='import', created_at__date=current
            ).count()
            deletes_count = ContentImportLog.objects.filter(
                action='delete', created_at__date=current
            ).count()
            if imports_count or deletes_count:
                self.stdout.write(
                    f'  {current:%d/%m}  +{imports_count} importados  -{deletes_count} eliminados'
                )
            current += timedelta(days=1)

        total_i = ContentImportLog.objects.filter(
            action='import',
            created_at__date__gte=start,
            created_at__date__lte=end,
        ).count()
        total_d = ContentImportLog.objects.filter(
            action='delete',
            created_at__date__gte=start,
            created_at__date__lte=end,
        ).count()
        self.stdout.write(f'\n  Total del período: +{total_i} importados  -{total_d} eliminados\n')

    def _print_imports(self, qs):
        count = qs.count()
        self.stdout.write(f'\nIMPORTADOS: {count} videos')
        if not count:
            return
        by_category = (
            qs.values('category', 'source_type')
            .annotate(total=Count('id'))
            .order_by('-total')
        )
        for row in by_category:
            cat = row["category"] or "(sin categoría)"
            self.stdout.write(
                f'  • {cat:<14} — '
                f'{row["total"]:>3} ({row["source_type"]})'
            )
        by_author = qs.values('author_name').annotate(total=Count('id')).order_by('-total')[:5]
        if by_author:
            self.stdout.write('\n  Top autores del día:')
            for row in by_author:
                self.stdout.write(f'    – {row["author_name"]} ({row["total"]} videos)')

    def _print_deletes(self, qs):
        count = qs.count()
        self.stdout.write(f'\nELIMINADOS: {count} videos')
        if not count:
            return
        for log in qs.order_by('-created_at')[:20]:
            self.stdout.write(
                f'  • {log.external_id:<25} [{log.category}] '
                f'{log.source_type} — {log.license}'
            )
            if log.notes:
                self.stdout.write(f'    Nota: {log.notes[:120]}')

    def _print_db_summary(self):
        self.stdout.write(f'\n{"="*55}')
        self.stdout.write('  RESUMEN GLOBAL — estado actual de la DB')
        self.stdout.write(f'{"="*55}')

        total = Video.objects.count()
        ugc = Video.objects.filter(source_type='ugc').count()
        pexels = Video.objects.filter(source_type='pexels').count()
        pixabay = Video.objects.filter(source_type='pixabay').count()
        archive = Video.objects.filter(source_type='archive').count()

        self.stdout.write(f'\nTotal de videos: {total}')
        self.stdout.write(f'  * UGC (usuarios):      {ugc}')
        self.stdout.write(f'  * Pexels:              {pexels}')
        self.stdout.write(f'  * Pixabay:             {pixabay}')
        self.stdout.write(f'  * Internet Archive:    {archive}')

        self.stdout.write('\nPor categoría (catálogo licenciado):')
        by_cat = (
            Video.objects
            .exclude(source_type='ugc')
            .values('category')
            .annotate(total=Count('id'))
            .order_by('-total')
        )
        for row in by_cat:
            cat = row["category"] or "(sin categoría)"
            self.stdout.write(f'  • {cat:<14} {row["total"]:>4} videos')

        self.stdout.write('\nLogs históricos:')
        total_imports = ContentImportLog.objects.filter(action='import').count()
        total_deletes = ContentImportLog.objects.filter(action='delete').count()
        self.stdout.write(f'  • Total importados: {total_imports}')
        self.stdout.write(f'  • Total eliminados: {total_deletes}')

        first_log = ContentImportLog.objects.order_by('created_at').first()
        if first_log:
            self.stdout.write(f'  • Primer import:    {first_log.created_at:%d/%m/%Y}')

        self.stdout.write('')
