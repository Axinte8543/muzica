                                               

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0008_list_public_and_listlike'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReviewComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.RenameIndex(
            model_name='listlike',
            new_name='interaction_list_id_d647e2_idx',
            old_name='listlike_list_created_idx',
        ),
        migrations.RenameIndex(
            model_name='listlike',
            new_name='interaction_user_id_56f744_idx',
            old_name='listlike_user_created_idx',
        ),
        migrations.AddField(
            model_name='reviewcomment',
            name='review',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='interactions.albumreview'),
        ),
        migrations.AddField(
            model_name='reviewcomment',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='review_comments', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddIndex(
            model_name='reviewcomment',
            index=models.Index(fields=['review', 'created_at'], name='interaction_review__d96148_idx'),
        ),
        migrations.AddIndex(
            model_name='reviewcomment',
            index=models.Index(fields=['user', 'created_at'], name='interaction_user_id_cd6ce6_idx'),
        ),
    ]
