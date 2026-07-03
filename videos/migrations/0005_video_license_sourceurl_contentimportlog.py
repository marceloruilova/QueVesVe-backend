from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0004_video_category_source'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='license',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='video',
            name='source_url',
            field=models.URLField(blank=True),
        ),
        migrations.CreateModel(
            name='ContentImportLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('import', 'Importado'), ('delete', 'Eliminado')], max_length=20)),
                ('source_type', models.CharField(
                    choices=[('ugc', 'Usuario'), ('pexels', 'Pexels'), ('pixabay', 'Pixabay')],
                    max_length=20,
                )),
                ('category', models.CharField(blank=True, max_length=50)),
                ('external_id', models.CharField(blank=True, max_length=100)),
                ('author_name', models.CharField(blank=True, max_length=200)),
                ('license', models.CharField(blank=True, max_length=100)),
                ('source_url', models.URLField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('video', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='import_logs',
                    to='videos.video',
                )),
            ],
            options={
                'verbose_name': 'Log de contenido',
                'verbose_name_plural': 'Logs de contenido',
                'ordering': ['-created_at'],
            },
        ),
    ]
