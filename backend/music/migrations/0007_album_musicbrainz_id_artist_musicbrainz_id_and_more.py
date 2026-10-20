                                               

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0006_artist_is_romanian'),
    ]

    operations = [
        migrations.AddField(
            model_name='album',
            name='musicbrainz_id',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='artist',
            name='musicbrainz_id',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='song',
            name='musicbrainz_id',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
    ]
