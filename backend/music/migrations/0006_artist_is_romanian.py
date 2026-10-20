                                               

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0005_album_spotify_id_album_spotify_url_artist_popularity_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='artist',
            name='is_romanian',
            field=models.BooleanField(default=False),
        ),
    ]
