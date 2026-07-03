from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0003_video_views_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='category',
            field=models.CharField(
                blank=True,
                choices=[
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
                ],
                db_index=True,
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name='video',
            name='source_type',
            field=models.CharField(
                choices=[
                    ('ugc', 'Usuario'),
                    ('pexels', 'Pexels'),
                    ('pixabay', 'Pixabay'),
                ],
                default='ugc',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='video',
            name='author_name',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='video',
            name='external_id',
            field=models.CharField(blank=True, db_index=True, max_length=100),
        ),
    ]
