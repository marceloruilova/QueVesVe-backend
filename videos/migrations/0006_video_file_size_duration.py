from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0005_video_license_sourceurl_contentimportlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='file_size',
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='video',
            name='duration_seconds',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
