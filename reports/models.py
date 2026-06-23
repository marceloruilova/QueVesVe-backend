from django.db import models
from django.conf import settings


REPORT_REASONS = [
    ('spam', 'Spam o contenido falso'),
    ('inappropriate', 'Contenido inapropiado o adulto'),
    ('harassment', 'Acoso o bullying'),
    ('copyright', 'Violación de derechos de autor'),
    ('misinformation', 'Desinformación'),
    ('other', 'Otro'),
]


class ContentReport(models.Model):
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reports_made',
    )
    video = models.ForeignKey(
        'videos.Video',
        on_delete=models.CASCADE,
        related_name='reports',
    )
    reason = models.CharField(max_length=30, choices=REPORT_REASONS)
    details = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('reporter', 'video')
        ordering = ['-created_at']

    def __str__(self):
        return f"Report by {self.reporter} on video {self.video_id} — {self.reason}"


class CopyrightReport(models.Model):
    reporter_name = models.CharField(max_length=200)
    reporter_email = models.EmailField()
    video = models.ForeignKey(
        'videos.Video',
        on_delete=models.CASCADE,
        related_name='copyright_reports',
    )
    work_description = models.TextField(max_length=1000)
    original_url = models.URLField(blank=True)
    good_faith_statement = models.BooleanField(default=False)
    accuracy_statement = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Copyright report by {self.reporter_email} on video {self.video_id}"
