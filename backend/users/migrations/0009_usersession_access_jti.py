                                               

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_revokedtoken_usersession_webauthncredential'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersession',
            name='access_jti',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
