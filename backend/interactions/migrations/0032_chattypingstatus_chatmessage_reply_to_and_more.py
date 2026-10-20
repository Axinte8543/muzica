                                               

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0031_remove_chatmessage_interaction_created_5d4975_idx_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatTypingStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_typing', models.BooleanField(default=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='reply_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replies', to='interactions.chatmessage'),
        ),
        migrations.AddIndex(
            model_name='chatmessage',
            index=models.Index(fields=['reply_to'], name='interaction_reply_t_61f463_idx'),
        ),
        migrations.AddField(
            model_name='chattypingstatus',
            name='partner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='typing_statuses_for_partner', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='chattypingstatus',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='typing_statuses', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddIndex(
            model_name='chattypingstatus',
            index=models.Index(fields=['partner', 'is_typing', '-updated_at'], name='interaction_partner_7226df_idx'),
        ),
        migrations.AddIndex(
            model_name='chattypingstatus',
            index=models.Index(fields=['user', 'partner'], name='interaction_user_id_9bce9b_idx'),
        ),
        migrations.AddConstraint(
            model_name='chattypingstatus',
            constraint=models.UniqueConstraint(fields=('user', 'partner'), name='unique_typing_status_per_pair'),
        ),
    ]
