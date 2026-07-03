import os
import subprocess
import tempfile
from pathlib import Path

import requests
from decouple import config
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from videos.models import ContentImportLog, Video

User = get_user_model()

PEXELS_VIDEO_SEARCH = 'https://api.pexels.com/videos/search'
PEXELS_LICENSE = 'Pexels License'
PEXELS_LICENSE_URL = 'https://www.pexels.com/license/'

CATEGORY_QUERY = {
    'naturaleza': 'nature landscape',
    'animales': 'animals wildlife',
    'comida': 'food cooking',
    'autos': 'cars automotive',
    'viajes': 'travel destinations',
    'tecnologia': 'technology digital',
    'deporte': 'sports fitness',
    'musica': 'music performance',
    'humor': 'funny comedy',
    'educacion': 'education learning',
}

VALID_CATEGORIES = list(CATEGORY_QUERY.keys())


class Command(BaseCommand):
    help = (
        'Descarga videos de Pexels (uso comercial libre — Pexels License) '
        'por categoría y los registra como contenido semilla con trazabilidad completa.\n\n'
        'Requiere PEXELS_API_KEY en el .env.\n\n'
        'Ejemplos:\n'
        '  python manage.py fetch_pexels naturaleza animales\n'
        '  python manage.py fetch_pexels naturaleza --count 50\n'
        '  python manage.py fetch_pexels naturaleza --dry-run\n\n'
        f'Categorías válidas: {", ".join(VALID_CATEGORIES)}'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'categories',
            nargs='+',
            metavar='categoria',
            help=f'Una o más categorías: {", ".join(VALID_CATEGORIES)}',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            metavar='N',
            help='Máximo de videos a descargar por categoría (default: 20)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué haría sin descargar ni guardar nada',
        )

    def handle(self, *args, **options):
        api_key = config('PEXELS_API_KEY', default='')
        if not api_key and not options['dry_run']:
            raise CommandError(
                'PEXELS_API_KEY no está configurada en el .env.\n'
                'Obtené una gratis en https://www.pexels.com/api/\n'
                f'Licencia del contenido: {PEXELS_LICENSE} — uso comercial libre, atribución recomendada.'
            )

        dry_run = options['dry_run']
        count = options['count']
        categories = options['categories']

        for cat in categories:
            if cat not in VALID_CATEGORIES:
                raise CommandError(
                    f'Categoría inválida: "{cat}". '
                    f'Válidas: {", ".join(VALID_CATEGORIES)}'
                )

        seed_user = None
        if not dry_run:
            seed_user = self._get_or_create_seed_user()

        total_fetched = total_skipped = 0

        for cat in categories:
            fetched, skipped = self._process_category(cat, api_key, count, seed_user, dry_run)
            total_fetched += fetched
            total_skipped += skipped

        prefix = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{prefix}Listo — '
                f'{total_fetched} videos importados | '
                f'{total_skipped} omitidos (ya existían o sin calidad ≤1080p)\n'
                f'Todos bajo {PEXELS_LICENSE} — {PEXELS_LICENSE_URL}'
            )
        )

    # ------------------------------------------------------------------

    def _get_or_create_seed_user(self):
        username = 'pexels_content'
        user = User.objects.filter(username=username).first()
        if user:
            return user
        user = User.objects.create_user(
            username=username,
            email='pexels@seed.internal',
            password='PexelsSeed2026!',
            bio='Contenido licenciado de Pexels (pexels.com) — uso comercial libre.',
        )
        self.stdout.write(self.style.SUCCESS(f'[+] Usuario semilla creado: {username}'))
        return user

    def _process_category(self, category, api_key, count, seed_user, dry_run):
        query = CATEGORY_QUERY[category]
        self.stdout.write(f'\n→ Categoría: {category} (query: "{query}")')

        pexels_videos = self._search_pexels(api_key, query, count, dry_run)
        if not pexels_videos:
            self.stdout.write('  [!] Sin resultados de Pexels.')
            return 0, 0

        fetched = skipped = 0
        for pv in pexels_videos[:count]:
            result = self._import_video(pv, category, seed_user, dry_run)
            if result:
                fetched += 1
            else:
                skipped += 1

        return fetched, skipped

    def _search_pexels(self, api_key, query, count, dry_run):
        if dry_run:
            self.stdout.write(
                f'  [dry] GET {PEXELS_VIDEO_SEARCH}?query={query}&per_page={min(count, 80)}'
            )
            return [{'id': 'DRY', 'user': {'name': 'DryAuthor', 'url': ''}, 'video_files': [], 'url': ''}]

        per_page = min(count, 80)
        try:
            resp = requests.get(
                PEXELS_VIDEO_SEARCH,
                headers={'Authorization': api_key},
                params={'query': query, 'per_page': per_page},
                timeout=15,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            self.stderr.write(f'  [!] Error llamando a Pexels: {e}')
            return []

        return resp.json().get('videos', [])

    def _import_video(self, pv, category, seed_user, dry_run):
        external_id = f'pexels_{pv["id"]}'
        author = pv.get('user', {}).get('name', 'Pexels')
        source_url = pv.get('url', '')

        if dry_run:
            self.stdout.write(
                f'  [dry] Video {pv["id"]} — autor: {author} — licencia: {PEXELS_LICENSE}'
            )
            return True

        if Video.objects.filter(external_id=external_id).exists():
            self.stdout.write(f'  [~] Ya existe: {external_id}')
            return False

        video_url = self._pick_best_file(pv.get('video_files', []))
        if not video_url:
            self.stdout.write(f'  [!] Sin calidad ≤1080p para: {pv["id"]}')
            return False

        return self._download_and_save(pv, video_url, external_id, author, source_url, category, seed_user)

    def _pick_best_file(self, video_files):
        """Elige el archivo de mayor resolución ≤1080p. Los videos de Pexels son libres de uso comercial."""
        candidates = [
            vf for vf in video_files
            if vf.get('height', 0) <= 1080 and vf.get('link')
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda vf: vf.get('height', 0))['link']

    def _download_and_save(self, pv, video_url, external_id, author, source_url, category, seed_user):
        self.stdout.write(f'  ↓ Descargando {pv["id"]} — {PEXELS_LICENSE} …')
        try:
            resp = requests.get(video_url, stream=True, timeout=60)
            resp.raise_for_status()
        except requests.RequestException as e:
            self.stderr.write(f'  [!] Error descargando {pv["id"]}: {e}')
            return False

        filename = f'pexels_{pv["id"]}.mp4'
        tmp_dir = tempfile.mkdtemp()
        tmp_path = Path(tmp_dir) / filename

        try:
            with open(tmp_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    f.write(chunk)

            description = (
                source_url.rstrip('/').split('/')[-2].replace('-', ' ').title()
                if source_url else f'Video de {category}'
            )

            video = Video(
                user=seed_user,
                description=description,
                tags=category,
                category=category,
                source_type='pexels',
                author_name=author,
                external_id=external_id,
                license=PEXELS_LICENSE,
                source_url=source_url,
            )

            with open(tmp_path, 'rb') as vf:
                video.video_file.save(filename, File(vf), save=False)

            thumb_path = self._extract_thumbnail(tmp_path)
            if thumb_path:
                with open(thumb_path, 'rb') as tf:
                    video.thumbnail.save(f'thumb_{pv["id"]}.jpg', File(tf), save=False)
                os.remove(thumb_path)

            video.save()

            ContentImportLog.objects.create(
                video=video,
                action='import',
                source_type='pexels',
                category=category,
                external_id=external_id,
                author_name=author,
                license=PEXELS_LICENSE,
                source_url=source_url,
                notes=f'Importado automáticamente — query: {CATEGORY_QUERY[category]}',
            )

            self.stdout.write(self.style.SUCCESS(f'  [+] {external_id} — {author} [{PEXELS_LICENSE}]'))
            return True

        finally:
            if tmp_path.exists():
                tmp_path.unlink()
            try:
                os.rmdir(tmp_dir)
            except OSError:
                pass

    def _extract_thumbnail(self, video_path):
        out = Path(str(video_path) + '_thumb.jpg')
        try:
            result = subprocess.run(
                ['ffmpeg', '-y', '-i', str(video_path), '-ss', '00:00:01', '-vframes', '1', str(out)],
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0 and out.exists():
                return str(out)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None
