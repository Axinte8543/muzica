from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

	dependencies = [
		('music', '0009_artistsimilarity'),
		('interactions', '0010_favoritealbum'),
	]

	operations = [
		migrations.CreateModel(
			name='WantToListen',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('album', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wanted_by', to='music.album')),
				('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='want_to_listen', to=settings.AUTH_USER_MODEL)),
			],
			options={
				'ordering': ['-created_at', '-id'],
			},
		),
		migrations.AddConstraint(
			model_name='wanttolisten',
			constraint=models.UniqueConstraint(fields=('user', 'album'), name='unique_want_to_listen_per_user_album'),
		),
		migrations.AddIndex(
			model_name='wanttolisten',
			index=models.Index(fields=['user', '-created_at'], name='w2l_user_created_idx'),
		),
		migrations.AddIndex(
			model_name='wanttolisten',
			index=models.Index(fields=['album', '-created_at'], name='w2l_album_created_idx'),
		),
	]
