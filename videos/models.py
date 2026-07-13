from django.db import models
from django.conf import settings

CATEGORIES = [
    ('naturaleza', 'Naturaleza'),
    ('animales', 'Animales'),
    ('comida', 'Comida'),
    ('autos', 'Autos'),
    ('viajes', 'Viajes'),
    ('tecnologia', 'Tecnología'),
    ('deporte', 'Deporte'),
    ('musica', 'Música'),
    ('humor', 'Humor'),
    ('educacion', 'Educación'),
]

SOURCE_TYPES = [
    ('ugc', 'Usuario'),
    ('pexels', 'Pexels'),
    ('pixabay', 'Pixabay'),
    ('archive', 'Internet Archive'),
]


class Video(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='videos')
    video_file = models.FileField(upload_to='videos/')
    thumbnail = models.ImageField(upload_to='thumbnails/', null=True, blank=True)
    description = models.TextField(max_length=500, blank=True)
    music = models.CharField(max_length=200, blank=True)
    tags = models.CharField(max_length=500, blank=True)
    comments_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=50, choices=CATEGORIES, blank=True, db_index=True)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES, default='ugc')
    author_name = models.CharField(max_length=200, blank=True)
    external_id = models.CharField(max_length=100, blank=True, db_index=True)
    license = models.CharField(max_length=100, blank=True)
    source_url = models.URLField(blank=True)

    @property
    def likes_count(self):
        return self.likes.count()

    class Meta:
        ordering = ['-created_at']


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='likes')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'video')


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


LOG_ACTIONS = [
    ('import', 'Importado'),
    ('delete', 'Eliminado'),
]


class ContentImportLog(models.Model):
    """Registro diario de videos importados/eliminados del catálogo licenciado."""
    video = models.ForeignKey(
        Video,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='import_logs',
    )
    action = models.CharField(max_length=20, choices=LOG_ACTIONS)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    category = models.CharField(max_length=50, blank=True)
    external_id = models.CharField(max_length=100, blank=True)
    author_name = models.CharField(max_length=200, blank=True)
    license = models.CharField(max_length=100, blank=True)
    source_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Log de contenido'
        verbose_name_plural = 'Logs de contenido'

    def __str__(self):
        return f'{self.get_action_display()} — {self.external_id} ({self.created_at:%Y-%m-%d})'
