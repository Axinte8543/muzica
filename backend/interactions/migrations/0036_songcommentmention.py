                                         

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0035_analyticsevent'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SongCommentMention',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mentions', to='interactions.songcomment')),
                ('mentioned_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='song_comment_mentions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['mentioned_user', '-created_at'], name='interaction_mentioned_1f8a28_idx'), models.Index(fields=['comment', '-created_at'], name='interaction_comment_9fb6a8_idx')],
                'constraints': [models.UniqueConstraint(fields=['comment', 'mentioned_user'], name='unique_song_comment_mention')],
            },
        ),
    ]
