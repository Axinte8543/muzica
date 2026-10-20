                                               

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0002_albumreviewlike'),
        ('music', '0002_song_artist_and_single_support'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='List',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lists', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ListAlbum',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('album', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='list_albums', to='music.album')),
                ('list', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='list_albums', to='interactions.list')),
            ],
            options={
                'ordering': ['-added_at'],
                'unique_together': {('list', 'album')},
            },
        ),
        migrations.AddField(
            model_name='list',
            name='albums',
            field=models.ManyToManyField(blank=True, related_name='in_lists', through='interactions.ListAlbum', to='music.album'),
        ),
        migrations.AddConstraint(
            model_name='list',
            constraint=models.UniqueConstraint(fields=('user', 'name'), name='unique_list_name_per_user'),
        ),
    ]
