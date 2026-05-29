from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0029_reactions'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlbumReviewReaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emoji', models.CharField(choices=[('👍', '👍 Thumbs Up'), ('❤️', '❤️ Heart'), ('😂', '😂 Laughing'), ('😮', '😮 Surprised'), ('😢', '😢 Sad'), ('🔥', '🔥 Fire'), ('👏', '👏 Clapping'), ('🎉', '🎉 Party')], max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('review', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='reactions', to='interactions.albumreview')),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='album_review_reactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
                'unique_together': {('user', 'review', 'emoji')},
            },
        ),
        migrations.AddIndex(
            model_name='albumreviewreaction',
            index=models.Index(fields=['review', 'emoji'], name='interaction_review_i_32cb42_idx'),
        ),
        migrations.AddIndex(
            model_name='albumreviewreaction',
            index=models.Index(fields=['user', '-created_at'], name='interaction_user_id_dfbf97_idx'),
        ),
    ]
