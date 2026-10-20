                                         

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0023_catalogchangelogevent_reviewcommentedit_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationpreferences',
            name='notify_artist_follows',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='notificationpreferences',
            name='notify_followed_artist_releases',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='notificationpreferences',
            name='notify_genre_releases',
            field=models.BooleanField(default=True),
        ),
    ]
