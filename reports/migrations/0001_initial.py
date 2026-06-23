from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('videos', '0003_video_views_count'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(choices=[('spam', 'Spam o contenido falso'), ('inappropriate', 'Contenido inapropiado o adulto'), ('harassment', 'Acoso o bullying'), ('copyright', 'Violación de derechos de autor'), ('misinformation', 'Desinformación'), ('other', 'Otro')], max_length=30)),
                ('details', models.TextField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed', models.BooleanField(default=False)),
                ('reporter', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reports_made', to=settings.AUTH_USER_MODEL)),
                ('video', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='videos.video')),
            ],
            options={
                'ordering': ['-created_at'],
                'unique_together': {('reporter', 'video')},
            },
        ),
        migrations.CreateModel(
            name='CopyrightReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reporter_name', models.CharField(max_length=200)),
                ('reporter_email', models.EmailField(max_length=254)),
                ('work_description', models.TextField(max_length=1000)),
                ('original_url', models.URLField(blank=True)),
                ('good_faith_statement', models.BooleanField(default=False)),
                ('accuracy_statement', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed', models.BooleanField(default=False)),
                ('video', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='copyright_reports', to='videos.video')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
