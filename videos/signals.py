from django.db.models.signals import post_delete
from django.dispatch import receiver


@receiver(post_delete, sender='videos.Video')
def log_licensed_video_deletion(sender, instance, **kwargs):
    from videos.models import ContentImportLog
    if instance.source_type not in ('pexels', 'pixabay'):
        return
    ContentImportLog.objects.create(
        video=None,
        action='delete',
        source_type=instance.source_type,
        category=instance.category,
        external_id=instance.external_id,
        author_name=instance.author_name,
        license=instance.license,
        source_url=instance.source_url,
        notes=f'Video eliminado — descripción: {instance.description[:200]}',
    )
