                                               

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('interactions', '0027_moderationreport_resolution_details'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='chatmessage',
            name='interaction_created_5d4975_idx',
        ),
        migrations.RemoveIndex(
            model_name='chatmessage',
            name='interaction_user_id_b84829_idx',
        ),
        migrations.RenameField(
            model_name='chatmessage',
            old_name='user',
            new_name='sender',
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='recipient',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='received_messages', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='is_read',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='chatmessage',
            name='sender',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_messages', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterModelOptions(
            name='chatmessage',
            options={'ordering': ['created_at']},
        ),
        migrations.AddIndex(
            model_name='chatmessage',
            index=models.Index(fields=['sender', 'recipient', '-created_at'], name='chat_msg_sender_recipient_idx'),
        ),
        migrations.AddIndex(
            model_name='chatmessage',
            index=models.Index(fields=['recipient', 'is_read'], name='chat_msg_recipient_unread_idx'),
        ),
    ]
