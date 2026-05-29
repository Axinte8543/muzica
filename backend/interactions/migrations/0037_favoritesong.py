from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0036_songcommentmention'),
        ('music', '0009_artistsimilarity'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FavoriteSong',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.PositiveSmallIntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4')])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('song', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorited_by', to='music.song')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorite_songs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['position', 'id'],
                'indexes': [models.Index(fields=['user', 'position'], name='fs_user_position_idx')],
                'constraints': [models.UniqueConstraint(fields=('user', 'position'), name='unique_favorite_song_position_per_user'), models.UniqueConstraint(fields=('user', 'song'), name='unique_favorite_song_per_user')],
            },
        ),
    ]