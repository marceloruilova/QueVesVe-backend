import os
import tempfile
from pathlib import Path

import requests
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from videos.models import ContentImportLog, Video

User = get_user_model()

ARCHIVE_SEARCH = 'https://archive.org/advancedsearch.php'
ARCHIVE_METADATA = 'https://archive.org/metadata/{identifier}'
ARCHIVE_DOWNLOAD = 'https://archive.org/download/{identifier}/{filename}'
ARCHIVE_THUMB = 'https://archive.org/services/img/{identifier}'
ARCHIVE_LICENSE = 'Public Domain (Internet Archive)'
ARCHIVE_LICENSE_URL = 'https://archive.org/about/terms.php'

MAX_API_VIDEOS = 100
MAX_DURATION_SECONDS = 300   # 5 minutos
MAX_FILE_SIZE_MB = 150       # descartamos archivos muy pesados

CATEGORY_QUERY = {
    'naturaleza': 'nature',
    'animales': 'animals',
    'comida': 'food',
    'autos': 'cars',
    'viajes': 'travel',
    'tecnologia': 'technology',
    'deporte': 'sports',
    'musica': 'music',
    'humor': 'comedy',
    'educacion': 'education',
}

VALID_CATEGORIES = list(CATEGORY_QUERY.keys())


class Command(BaseCommand):
    help = (
        'Descarga videos de dominio publico desde Internet Archive (sin API key).\n\n'
        'Todo el contenido es de dominio publico y libre de uso comercial.\n\n'
        'Ejemplos:\n'
        '  python manage.py fetch_archive naturaleza animales\n'
        '  python manage.py fetch_archive naturaleza --count 5\n'
        '  python manage.py fetch_archive naturaleza --dry-run\n\n'
        f'Categorias validas: {", ".join(VALID_CATEGORIES)}'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'categories',
            nargs='+',
            metavar='categoria',
            help=f'Una o mas categorias: {", ".join(VALID_CATEGORIES)}',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            metavar='N',
            help='Maximo de videos a importar por categoria (default: 10)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra que haria sin descargar ni guardar nada',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        count = options['count']
        categories = options['categories']

        for cat in categories:
            if cat not in VALID_CATEGORIES:
                raise CommandError(
                    f'Categoria invalida: "{cat}". '
                    f'Validas: {", ".join(VALID_CATEGORIES)}'
                )

        seed_user = None
        if not dry_run:
            seed_user = self._get_or_create_seed_user()

        total_fetched = total_skipped = 0
        for cat in categories:
            fetched, skipped = self._process_category(cat, count, seed_user, dry_run)
            total_fetched += fetched
            total_skipped += skipped

        prefix = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'\n{prefix}Listo -- {total_fetched} videos importados | {total_skipped} omitidos\n'
            f'Licencia: {ARCHIVE_LICENSE}\n'
            f'Referencia: {ARCHIVE_LICENSE_URL}'
        ))

    # ------------------------------------------------------------------

    def _get_or_create_seed_user(self):
        username = 'archive_content'
        user = User.objects.filter(username=username).first()
        if user:
            return user
        user = User.objects.create_user(
            username=username,
            email='archive@seed.internal',
            password='ArchiveSeed2026!',
            bio='Contenido de dominio publico — Internet Archive (archive.org).',
        )
        self.stdout.write(self.style.SUCCESS(f'[+] Usuario semilla creado: {username}'))
        return user

    def _process_category(self, category, count, seed_user, dry_run):
        query = CATEGORY_QUERY[category]
        self.stdout.write(f'\n>> Categoria: {category} (query: "{query}")')

        docs = self._search_archive(query, count)
        if not docs:
            self.stdout.write('  [!] Sin resultados en Internet Archive.')
            return 0, 0

        fetched = skipped = 0
        for doc in docs:
            if fetched >= count:
                break
            result = self._import_item(doc, category, seed_user, dry_run)
            if result:
                fetched += 1
            else:
                skipped += 1

        return fetched, skipped

    def _search_archive(self, query, count):
        try:
            resp = requests.get(
                ARCHIVE_SEARCH,
                params={
                    'q': f'mediatype:movies subject:{query}',
                    'fl[]': ['identifier', 'title', 'creator', 'description'],
                    'rows': min(count * 6, 80),  # pedimos mas por el filtrado de duracion
                    'output': 'json',
                    'sort[]': 'downloads desc',
                },
                timeout=20,
            )
            resp.raise_for_status()
            return resp.json().get('response', {}).get('docs', [])
        except requests.RequestException as e:
            self.stderr.write(f'  [!] Error buscando en Archive.org: {e}')
            return []

    def _import_item(self, doc, category, seed_user, dry_run):
        identifier = doc.get('identifier', '')
        if not identifier:
            return False

        external_id = f'archive_{identifier}'
        title = doc.get('title', identifier)
        creator = doc.get('creator', 'Internet Archive')
        if isinstance(creator, list):
            creator = ', '.join(str(c) for c in creator)
        creator = str(creator)[:200]

        if dry_run:
            self.stdout.write(
                f'  [dry] {identifier} -- {str(title)[:60]} -- {ARCHIVE_LICENSE}'
            )
            return True

        if Video.objects.filter(external_id=external_id).exists():
            self.stdout.write(f'  [~] Ya existe: {external_id}')
            return False

        video_url, duration = self._get_best_mp4(identifier)
        if not video_url:
            return False

        self._ensure_slot()
        return self._download_and_save(
            identifier, video_url, duration, title, creator, category, seed_user
        )

    def _get_best_mp4(self, identifier):
        """Busca el .mp4 mas pequeno dentro del limite de duracion y peso."""
        try:
            resp = requests.get(
                ARCHIVE_METADATA.format(identifier=identifier),
                timeout=15,
            )
            if not resp.ok:
                return None, 0

            files = resp.json().get('files', [])
            max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024

            mp4_files = [
                f for f in files
                if f.get('name', '').lower().endswith('.mp4')
                and float(f.get('size', float('inf'))) <= max_bytes
            ]

            if not mp4_files:
                self.stdout.write(f'  [!] {identifier}: sin .mp4 dentro del limite de {MAX_FILE_SIZE_MB}MB')
                return None, 0

            # Filtrar por duracion cuando el metadata la incluye
            valid = []
            for f in mp4_files:
                duration = float(f.get('length', 0))
                if duration == 0 or duration <= MAX_DURATION_SECONDS:
                    valid.append((f, duration))

            if not valid:
                self.stdout.write(f'  [!] {identifier}: todos los .mp4 superan los 5 min')
                return None, 0

            # El mas pequeno entre los validos
            best_file, best_duration = min(valid, key=lambda x: float(x[0].get('size', float('inf'))))
            url = ARCHIVE_DOWNLOAD.format(identifier=identifier, filename=best_file['name'])
            return url, best_duration

        except (requests.RequestException, ValueError, KeyError, TypeError) as e:
            self.stderr.write(f'  [!] Error obteniendo metadata de {identifier}: {e}')
            return None, 0

    def _ensure_slot(self):
        """Elimina el video API mas antiguo si el catalogo ya llego a MAX_API_VIDEOS."""
        count = Video.objects.filter(source_type__in=['pexels', 'pixabay', 'archive']).count()
        if count < MAX_API_VIDEOS:
            return
        oldest = Video.objects.filter(
            source_type__in=['pexels', 'pixabay', 'archive']
        ).order_by('created_at').first()
        if oldest:
            self.stdout.write(self.style.WARNING(
                f'  [limite] {MAX_API_VIDEOS} videos API alcanzado -- '
                f'eliminando {oldest.external_id} ({oldest.category}) para hacer espacio'
            ))
            oldest.delete()  # activa post_delete signal -> ContentImportLog

    def _download_and_save(self, identifier, video_url, duration, title, creator, category, seed_user):
        self.stdout.write(f'  >> Descargando {identifier} ({int(duration)}s) ...')
        try:
            resp = requests.get(video_url, stream=True, timeout=120)
            resp.raise_for_status()
        except requests.RequestException as e:
            self.stderr.write(f'  [!] Error descargando {identifier}: {e}')
            return False

        filename = f'archive_{identifier}.mp4'
        tmp_dir = tempfile.mkdtemp()
        tmp_path = Path(tmp_dir) / filename

        try:
            with open(tmp_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    f.write(chunk)

            description = str(title)[:200] if title else f'Video de {category}'

            video = Video(
                user=seed_user,
                description=description,
                tags=category,
                category=category,
                source_type='archive',
                author_name=creator,
                external_id=f'archive_{identifier}',
                license=ARCHIVE_LICENSE,
                source_url=f'https://archive.org/details/{identifier}',
            )

            with open(tmp_path, 'rb') as vf:
                video.video_file.save(filename, File(vf), save=False)

            # Archive.org provee thumbnails propios — no necesitamos ffmpeg
            self._save_thumbnail(video, identifier, tmp_dir)

            video.save()

            ContentImportLog.objects.create(
                video=video,
                action='import',
                source_type='archive',
                category=category,
                external_id=f'archive_{identifier}',
                author_name=creator,
                license=ARCHIVE_LICENSE,
                source_url=f'https://archive.org/details/{identifier}',
                notes=f'Importado automaticamente desde Internet Archive -- query: {CATEGORY_QUERY[category]}',
            )

            self.stdout.write(self.style.SUCCESS(
                f'  [+] archive_{identifier} -- {creator} [{ARCHIVE_LICENSE}]'
            ))
            return True

        finally:
            if tmp_path.exists():
                tmp_path.unlink()
            try:
                os.rmdir(tmp_dir)
            except OSError:
                pass

    def _save_thumbnail(self, video, identifier, tmp_dir):
        """Descarga el thumbnail de Archive.org (sin ffmpeg)."""
        thumb_url = ARCHIVE_THUMB.format(identifier=identifier)
        try:
            resp = requests.get(thumb_url, timeout=10)
            content_type = resp.headers.get('Content-Type', '')
            if resp.ok and content_type.startswith('image/'):
                thumb_path = Path(tmp_dir) / f'thumb_{identifier}.jpg'
                with open(thumb_path, 'wb') as tf:
                    tf.write(resp.content)
                with open(thumb_path, 'rb') as tf:
                    video.thumbnail.save(f'thumb_{identifier}.jpg', File(tf), save=False)
                os.remove(thumb_path)
        except requests.RequestException:
            pass  # thumbnail es opcional
