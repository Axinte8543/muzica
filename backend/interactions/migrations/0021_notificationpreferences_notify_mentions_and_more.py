                                               

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0020_reviewcomment_parent_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationpreferences',
            name='notify_mentions',
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name='ReviewCommentMention',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mentions', to='interactions.reviewcomment')),
                ('mentioned_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='review_comment_mentions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['mentioned_user', '-created_at'], name='interaction_mention_ef2dbf_idx'), models.Index(fields=['comment', '-created_at'], name='interaction_comment_685c12_idx')],
                'constraints': [models.UniqueConstraint(fields=('comment', 'mentioned_user'), name='unique_review_comment_mention')],
            },
        ),
    ]
