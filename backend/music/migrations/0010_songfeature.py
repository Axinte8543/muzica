from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

	dependencies = [
		('music', '0009_artistsimilarity'),
	]

	operations = [
		migrations.CreateModel(
			name='SongFeature',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('artist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='featured_on_songs', to='music.artist')),
				('song', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='features', to='music.song')),
			],
			options={
				'ordering': ['-created_at', '-id'],
			},
		),
		migrations.AddIndex(
			model_name='songfeature',
			index=models.Index(fields=['song', '-created_at'], name='sf_song_created_idx'),
		),
		migrations.AddIndex(
			model_name='songfeature',
			index=models.Index(fields=['artist', '-created_at'], name='sf_artist_created_idx'),
		),
		migrations.AddConstraint(
			model_name='songfeature',
			constraint=models.UniqueConstraint(fields=('song', 'artist'), name='unique_song_feature_per_song_artist'),
		),
	]
