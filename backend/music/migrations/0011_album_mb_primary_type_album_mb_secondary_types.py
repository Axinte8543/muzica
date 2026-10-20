                                               

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('music', '0010_songfeature'),
    ]

    operations = [
        migrations.AddField(
            model_name='album',
            name='mb_primary_type',
            field=models.CharField(blank=True, db_index=True, max_length=32),
        ),
        migrations.AddField(
            model_name='album',
            name='mb_secondary_types',
            field=models.TextField(blank=True, help_text='Comma-separated MusicBrainz secondary types'),
        ),
    ]
