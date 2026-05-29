from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('music', '0002_song_artist_and_single_support'),
	]

	operations = [
		migrations.AddField(
			model_name='artist',
			name='is_approved',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='album',
			name='is_approved',
			field=models.BooleanField(default=False),
		),
		migrations.AddField(
			model_name='song',
			name='is_approved',
			field=models.BooleanField(default=False),
		),
	]
