                                               

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0007_album_musicbrainz_id_artist_musicbrainz_id_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='album',
            name='slug',
            field=models.SlugField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='artist',
            name='slug',
            field=models.SlugField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='genre',
            name='slug',
            field=models.SlugField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='song',
            name='slug',
            field=models.SlugField(max_length=255, unique=True),
        ),
    ]
