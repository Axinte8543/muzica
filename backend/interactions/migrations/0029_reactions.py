                                         

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('interactions', '0028_chatmessage_dms'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReviewCommentReaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emoji', models.CharField(choices=[('👍', '👍 Thumbs Up'), ('❤️', '❤️ Heart'), ('😂', '😂 Laughing'), ('😮', '😮 Surprised'), ('😢', '😢 Sad'), ('🔥', '🔥 Fire'), ('👏', '👏 Clapping'), ('🎉', '🎉 Party')], max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reactions', to='interactions.reviewcomment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='review_comment_reactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='SongCommentReaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emoji', models.CharField(choices=[('👍', '👍 Thumbs Up'), ('❤️', '❤️ Heart'), ('😂', '😂 Laughing'), ('😮', '😮 Surprised'), ('😢', '😢 Sad'), ('🔥', '🔥 Fire'), ('👏', '👏 Clapping'), ('🎉', '🎉 Party')], max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reactions', to='interactions.songcomment')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='song_comment_reactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='reviewcommentreaction',
            unique_together={('user', 'comment', 'emoji')},
        ),
        migrations.AddIndex(
            model_name='reviewcommentreaction',
            index=models.Index(fields=['comment', 'emoji'], name='interactions_reviewc_comment_69d8c6_idx'),
        ),
        migrations.AddIndex(
            model_name='reviewcommentreaction',
            index=models.Index(fields=['user', '-created_at'], name='interactions_reviewc_user_id_f8b2a7_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='songcommentreaction',
            unique_together={('user', 'comment', 'emoji')},
        ),
        migrations.AddIndex(
            model_name='songcommentreaction',
            index=models.Index(fields=['comment', 'emoji'], name='interactions_songc_comment_8f9c2e_idx'),
        ),
        migrations.AddIndex(
            model_name='songcommentreaction',
            index=models.Index(fields=['user', '-created_at'], name='interactions_songc_user_id_c4a8e9_idx'),
        ),
    ]
