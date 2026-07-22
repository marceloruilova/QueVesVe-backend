from decouple import config
from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import FileSystemStorage
from django.core.management.base import BaseCommand, CommandError

from storages.backends.s3 import S3Storage

from users.models.custom_user_models import CustomUser
from videos.models import Video

FIELD_GROUPS = {
    'videos': (Video, 'video_file'),
    'thumbnails': (Video, 'thumbnail'),
    'profile_pictures': (CustomUser, 'profile_picture'),
}


class Command(BaseCommand):
    help = (
        'Migra los archivos de media (videos, thumbnails, fotos de perfil) del '
        'filesystem local (MEDIA_ROOT) a Cloudflare R2, preservando el mismo nombre '
        'relativo que ya está guardado en la DB. Solo copia -- no borra nada local. '
        'Requiere las variables R2_* en el entorno aunque USE_R2_STORAGE todavía esté '
        'en False (así se puede migrar antes de activar el storage remoto).\n\n'
        'Ejemplos:\n'
        '  python manage.py migrate_media_to_r2 --dry-run\n'
        '  python manage.py migrate_media_to_r2 --only profile_pictures\n'
        '  python manage.py migrate_media_to_r2 --only videos --limit 100\n'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--only',
            choices=list(FIELD_GROUPS),
            metavar='GRUPO',
            help='Migrar sólo un grupo (videos, thumbnails, profile_pictures). Default: todos.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            metavar='N',
            help='Maximo de archivos a migrar por grupo en esta corrida (default: todos)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué se migraría sin subir ni escribir nada',
        )

    def handle(self, *args, **options):
        only = options['only']
        limit = options['limit']
        dry_run = options['dry_run']
        prefix = '[DRY RUN] ' if dry_run else ''

        source_storage = FileSystemStorage(location=settings.MEDIA_ROOT)
        dest_storage = self._build_dest_storage()

        groups = [only] if only else list(FIELD_GROUPS)

        grand_total = {'migrated': 0, 'skipped': 0, 'missing': 0, 'bytes': 0}

        for group in groups:
            model, field_name = FIELD_GROUPS[group]
            self.stdout.write(f'\n== {group} ==')
            stats = self._migrate_group(
                model, field_name, source_storage, dest_storage, limit, dry_run, prefix,
            )
            for key in grand_total:
                grand_total[key] += stats[key]

        self.stdout.write(self.style.SUCCESS(
            f"\n{prefix}Listo -- {grand_total['migrated']} migrados, "
            f"{grand_total['skipped']} ya existían, {grand_total['missing']} sin archivo "
            f"origen, ~{self._human(grand_total['bytes'])} subidos."
        ))

    # ------------------------------------------------------------------

    def _build_dest_storage(self):
        # Lee las credenciales directo del entorno (no de settings.STORAGES), para que este
        # comando funcione sin importar si USE_R2_STORAGE está en True o False todavía.
        try:
            return S3Storage(
                access_key=config('R2_ACCESS_KEY_ID'),
                secret_key=config('R2_SECRET_ACCESS_KEY'),
                bucket_name=config('R2_BUCKET_NAME'),
                endpoint_url=config('R2_ENDPOINT_URL'),
                region_name='auto',
                signature_version='s3v4',
                addressing_style='virtual',
                custom_domain=config('R2_PUBLIC_DOMAIN'),
                querystring_auth=False,
                file_overwrite=True,
                default_acl=None,
            )
        except Exception as exc:
            raise CommandError(f'No se pudo inicializar el storage de R2: {exc}') from exc

    def _migrate_group(self, model, field_name, source_storage, dest_storage, limit, dry_run, prefix):
        qs = model.objects.exclude(**{field_name: ''}).order_by('id')
        if limit:
            qs = qs[:limit]

        migrated = skipped = missing = 0
        total_bytes = 0

        for obj in qs:
            field_file = getattr(obj, field_name)
            name = field_file.name
            if not name:
                continue

            if not source_storage.exists(name):
                self.stdout.write(self.style.WARNING(f'  [!] falta archivo origen: {name}'))
                missing += 1
                continue

            if dest_storage.exists(name):
                skipped += 1
                continue

            size = source_storage.size(name)
            self.stdout.write(f'  {prefix}[+] {name} ({self._human(size)})')

            if not dry_run:
                with source_storage.open(name, 'rb') as f:
                    dest_storage._save(name, File(f))  # noqa: SLF001 -- preserva el name exacto

            migrated += 1
            total_bytes += size

        return {'migrated': migrated, 'skipped': skipped, 'missing': missing, 'bytes': total_bytes}

    @staticmethod
    def _human(num_bytes):
        value = float(num_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if value < 1024:
                return f'{value:.1f}{unit}'
            value /= 1024
        return f'{value:.1f}PB'
