                                               

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_emailverificationtoken_passwordresettoken'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprivacysettings',
            name='email_verified',
            field=models.BooleanField(default=False),
        ),
    ]
