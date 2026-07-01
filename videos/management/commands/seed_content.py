import json
import os
import shutil
import subprocess
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from videos.models import Video

User = get_user_model()


class Command(BaseCommand):
    help = 'Carga cuentas y videos semilla desde uno o varios JSON'

    def add_arguments(self, parser):
        parser.add_argument(
            'sources',
            nargs='+',
            metavar='json_or_dir',
            help='Archivo(s) JSON o directorio con archivos .json',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra lo que haría sin escribir nada en la base de datos',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            default=True,
            help='Omite usuarios y videos que ya existen (por defecto activado)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        skip_existing = options['skip_existing']

        json_files = self._collect_json_files(options['sources'])
        if not json_files:
            raise CommandError('No se encontraron archivos JSON en las rutas indicadas.')

        total_users = 0
        total_videos = 0
        skipped_users = 0
        skipped_videos = 0

        for json_path in json_files:
            self.stdout.write(f'\n→ Procesando {json_path}')
            accounts = self._load_json(json_path)

            for account_data in accounts:
                username = account_data.get('username', '').strip()
                if not username:
                    self.stderr.write('  [!] Entrada sin username, omitida.')
                    continue

                user, user_created = self._get_or_create_user(account_data, dry_run, skip_existing)
                if user_created:
                    total_users += 1
                    self.stdout.write(self.style.SUCCESS(f'  [+] Usuario creado: {username}'))
                else:
                    skipped_users += 1
                    self.stdout.write(f'  [~] Usuario existente: {username}')

                for video_data in account_data.get('videos', []):
                    created = self._create_video(video_data, user, dry_run, skip_existing, json_path)
                    if created:
                        total_videos += 1
                    else:
                        skipped_videos += 1

        prefix = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{prefix}Listo — '
                f'{total_users} usuarios creados, {skipped_users} omitidos | '
                f'{total_videos} videos creados, {skipped_videos} omitidos'
            )
        )

    # ------------------------------------------------------------------

    def _collect_json_files(self, sources):
        files = []
        for source in sources:
            p = Path(source)
            if p.is_dir():
                files.extend(sorted(p.glob('*.json')))
            elif p.is_file() and p.suffix == '.json':
                files.append(p)
            else:
                self.stderr.write(f'[!] No encontrado o no es JSON: {source}')
        return files

    def _load_json(self, path):
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            raise CommandError(f'El JSON {path} debe ser un array o un objeto.')
        return data

    def _get_or_create_user(self, data, dry_run, skip_existing):
        username = data['username'].strip()
        email = data.get('email', f'{username}@seed.internal').strip()
        password = data.get('password', 'SeedPass123!').strip()
        bio = data.get('bio', '').strip()

        existing = User.objects.filter(username=username).first()
        if existing:
            return existing, False

        if dry_run:
            fake = User(username=username, email=email, bio=bio)
            fake.pk = -1
            return fake, True

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            bio=bio,
        )

        avatar_path = data.get('profile_picture')
        if avatar_path:
            abs_path = Path(avatar_path)
            if abs_path.exists():
                with open(abs_path, 'rb') as img:
                    user.profile_picture.save(abs_path.name, File(img), save=True)
            else:
                self.stderr.write(f'    [!] Avatar no encontrado: {avatar_path}')

        return user, True

    def _create_video(self, data, user, dry_run, skip_existing, json_path):
        file_path = Path(data.get('file', ''))
        description = data.get('description', '').strip()
        tags = data.get('tags', '').strip()
        music = data.get('music', '').strip()
        thumbnail_path = data.get('thumbnail')

        if not file_path.exists():
            self.stderr.write(f'    [!] Video no encontrado: {file_path}')
            return False

        if skip_existing:
            exists = Video.objects.filter(
                user=user,
                description=description,
                video_file__endswith=file_path.name,
            ).exists()
            if exists:
                self.stdout.write(f'    [~] Video ya existe: {file_path.name}')
                return False

        if dry_run:
            self.stdout.write(f'    [+] (dry) Video: {file_path.name} → {user.username}')
            return True

        video = Video(
            user=user,
            description=description,
            tags=tags,
            music=music,
        )

        with open(file_path, 'rb') as vf:
            video.video_file.save(file_path.name, File(vf), save=False)

        if thumbnail_path:
            thumb = Path(thumbnail_path)
            if thumb.exists():
                with open(thumb, 'rb') as tf:
                    video.thumbnail.save(thumb.name, File(tf), save=False)
        else:
            generated = self._extract_thumbnail(file_path)
            if generated:
                with open(generated, 'rb') as tf:
                    video.thumbnail.save(f'thumb_{file_path.stem}.jpg', File(tf), save=False)
                os.remove(generated)

        video.save()
        self.stdout.write(self.style.SUCCESS(f'    [+] Video: {file_path.name} → {user.username}'))
        return True

    def _extract_thumbnail(self, video_path):
        """Extrae el primer frame con ffmpeg si está disponible."""
        out = Path(str(video_path) + '_thumb_tmp.jpg')
        try:
            result = subprocess.run(
                [
                    'ffmpeg', '-y', '-i', str(video_path),
                    '-ss', '00:00:01', '-vframes', '1',
                    str(out),
                ],
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0 and out.exists():
                return str(out)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None
