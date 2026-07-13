import json
import os
import subprocess
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from videos.models import Video

User = get_user_model()

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}
VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}

MAX_DURATION_SECONDS = 300  # 5 minutos


class Command(BaseCommand):
    help = (
        'Sube videos semilla desde carpetas. '
        'El nombre de cada carpeta es el username de la cuenta.\n\n'
        'Ejemplos:\n'
        '  python manage.py seed_content ../seed_data/juegos/\n'
        '  python manage.py seed_content ../seed_data/\n'
        '  python manage.py seed_content ../seed_data/juegos/ ../seed_data/deportes/\n'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'paths',
            nargs='+',
            metavar='carpeta',
            help='Carpeta de cuenta (o carpeta padre con subcarpetas de cuentas)',
        )
        parser.add_argument('--dry-run', action='store_true', help='Muestra lo que haría sin escribir nada')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        account_dirs = []

        for raw in options['paths']:
            p = Path(raw).resolve()
            if not p.is_dir():
                raise CommandError(f'No existe el directorio: {p}')
            account_dirs.extend(self._resolve_accounts(p))

        if not account_dirs:
            raise CommandError('No se encontraron carpetas de cuentas con videos.')

        total_users = total_videos = skipped = 0

        for account_dir in account_dirs:
            u_created, v_created, v_skipped = self._process_account(account_dir, dry_run)
            total_users += u_created
            total_videos += v_created
            skipped += v_skipped

        prefix = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{prefix}Listo — '
                f'{total_users} cuentas creadas | '
                f'{total_videos} videos subidos | '
                f'{skipped} omitidos'
            )
        )

    # ------------------------------------------------------------------

    def _resolve_accounts(self, path):
        """
        Si la carpeta tiene .mp4 directo → es una cuenta.
        Si tiene subcarpetas → cada subcarpeta es una cuenta.
        """
        videos_here = [f for f in path.iterdir() if f.suffix.lower() in VIDEO_EXTS]
        if videos_here:
            return [path]
        subdirs = [d for d in path.iterdir() if d.is_dir()]
        return subdirs

    def _process_account(self, account_dir, dry_run):
        username = account_dir.name
        meta = self._load_meta(account_dir)

        email = meta.get('email', f'{username}@seed.internal')
        password = meta.get('password', 'SeedPass123!')
        bio = meta.get('bio', '')
        default_tags = meta.get('default_tags', '')
        default_music = meta.get('default_music', '')
        avatar_path = meta.get('profile_picture')

        self.stdout.write(f'\n→ Cuenta: {username}')

        user_created = 0
        existing = User.objects.filter(username=username).first()

        if existing:
            user = existing
            self.stdout.write(f'  [~] Usuario existente: {username}')
        else:
            if not dry_run:
                user = User.objects.create_user(username=username, email=email, password=password, bio=bio)
                if avatar_path:
                    ap = Path(avatar_path)
                    if ap.exists():
                        with open(ap, 'rb') as f:
                            user.profile_picture.save(ap.name, File(f), save=True)
                    else:
                        self.stderr.write(f'  [!] Avatar no encontrado: {avatar_path}')
            else:
                user = User(username=username, email=email)
                user.pk = -1
            self.stdout.write(self.style.SUCCESS(f'  [+] Usuario creado: {username}'))
            user_created = 1

        videos_created = 0
        videos_skipped = 0

        video_files = sorted(f for f in account_dir.iterdir() if f.suffix.lower() in VIDEO_EXTS)
        for vf in video_files:
            created = self._upload_video(vf, user, default_tags, default_music, dry_run)
            if created:
                videos_created += 1
            else:
                videos_skipped += 1

        return user_created, videos_created, videos_skipped

    def _upload_video(self, video_path, user, default_tags, default_music, dry_run):
        description = video_path.stem.replace('_', ' ').replace('-', ' ')

        if user.pk != -1:
            already = Video.objects.filter(
                user=user,
                video_file__endswith=video_path.name,
            ).exists()
            if already:
                self.stdout.write(f'  [~] Ya existe: {video_path.name}')
                return False

        duration = self._get_duration_seconds(video_path)
        if duration is not None and duration > MAX_DURATION_SECONDS:
            mins, secs = divmod(int(duration), 60)
            self.stdout.write(
                self.style.WARNING(
                    f'  [!] {video_path.name} dura {mins}:{secs:02d} min (máx 5:00) — omitido'
                )
            )
            return False

        if dry_run:
            self.stdout.write(f'  [+] (dry) {video_path.name}')
            return True

        video = Video(user=user, description=description, tags=default_tags, music=default_music)

        with open(video_path, 'rb') as vf:
            video.video_file.save(video_path.name, File(vf), save=False)

        thumb = self._extract_thumbnail(video_path)
        if thumb:
            with open(thumb, 'rb') as tf:
                video.thumbnail.save(f'thumb_{video_path.stem}.jpg', File(tf), save=False)
            os.remove(thumb)

        video.save()
        self.stdout.write(self.style.SUCCESS(f'  [+] {video_path.name}'))
        return True

    def _load_meta(self, account_dir):
        meta_path = account_dir / 'meta.json'
        if meta_path.exists():
            with open(meta_path, encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _get_duration_seconds(self, video_path):
        """Retorna duración en segundos, o None si ffprobe no está disponible."""
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(video_path)],
                capture_output=True, timeout=15, text=True,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return float(data.get('format', {}).get('duration', 0))
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, KeyError):
            pass
        return None

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
