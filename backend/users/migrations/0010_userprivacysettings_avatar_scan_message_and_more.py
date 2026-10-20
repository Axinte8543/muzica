                                               

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_usersession_access_jti'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprivacysettings',
            name='avatar_scan_message',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='userprivacysettings',
            name='avatar_scan_requested_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprivacysettings',
            name='avatar_scan_status',
            field=models.CharField(choices=[('idle', 'Idle'), ('pending', 'Pending'), ('clean', 'Clean'), ('rejected', 'Rejected'), ('failed', 'Failed')], default='idle', max_length=16),
        ),
        migrations.AddField(
            model_name='userprivacysettings',
            name='avatar_scanned_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprivacysettings',
            name='pending_avatar_key',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AddField(
            model_name='userprivacysettings',
            name='pending_avatar_url',
            field=models.URLField(blank=True, null=True),
        ),
    ]
