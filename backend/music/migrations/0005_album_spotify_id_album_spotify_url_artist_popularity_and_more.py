                                               

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0004_approve_existing_content'),
    ]

    operations = [
        migrations.AddField(
            model_name='album',
            name='spotify_id',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='album',
            name='spotify_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='artist',
            name='popularity',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='artist',
            name='spotify_id',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='artist',
            name='spotify_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='song',
            name='popularity',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='song',
            name='preview_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='song',
            name='spotify_id',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='song',
            name='spotify_url',
            field=models.URLField(blank=True),
        ),
    ]
