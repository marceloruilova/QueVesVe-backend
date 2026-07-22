import json
import subprocess

from django.conf import settings


def get_duration_seconds(path):
    """Retorna duración en segundos, o None si ffprobe no está disponible/falla."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(path)],
            capture_output=True, timeout=15, text=True,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data.get('format', {}).get('duration', 0))
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, KeyError):
        pass
    return None


def compress_video(input_path, output_path):
    """
    Recomprime el video a resolución/bitrate reducidos (ver settings UGC_COMPRESS_*).
    Retorna True si la compresión se aplicó, False si ffmpeg no está disponible o falló
    (en cuyo caso el llamador debe usar el archivo original sin comprimir).
    """
    max_height = settings.UGC_COMPRESS_MAX_HEIGHT
    video_bitrate = settings.UGC_COMPRESS_VIDEO_BITRATE
    audio_bitrate = settings.UGC_COMPRESS_AUDIO_BITRATE
    try:
        result = subprocess.run(
            [
                'ffmpeg', '-y', '-i', str(input_path),
                '-vf', f'scale=-2:min({max_height}\\,ih)',
                '-c:v', 'libx264', '-b:v', video_bitrate,
                '-c:a', 'aac', '-b:a', audio_bitrate,
                str(output_path),
            ],
            capture_output=True, timeout=300,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
