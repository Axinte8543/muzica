from django.db import migrations, models
import django.db.models.deletion


def forwards_fill_song_artist(apps, schema_editor):
	Song = apps.get_model('music', 'Song')
	# If a song already belongs to an album, infer artist from the album.
	for song in Song.objects.select_related('album__artist').filter(artist__isnull=True, album__isnull=False):
		song.artist_id = song.album.artist_id
		song.save(update_fields=['artist'])


def backwards_unfill_song_artist(apps, schema_editor):
	Song = apps.get_model('music', 'Song')
	# Best-effort rollback: if artist matches album artist, clear it.
	for song in Song.objects.select_related('album__artist').filter(album__isnull=False):
		if song.artist_id == song.album.artist_id:
			song.artist_id = None
			song.save(update_fields=['artist'])


class Migration(migrations.Migration):

	dependencies = [
		('music', '0001_initial'),
	]

	operations = [
		migrations.AlterField(
			model_name='song',
			name='album',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='songs', to='music.album'),
		),
		migrations.AlterField(
			model_name='song',
			name='track_number',
			field=models.PositiveIntegerField(blank=True, null=True),
		),
		migrations.AddField(
			model_name='song',
			name='artist',
			field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='songs', to='music.artist'),
		),
		migrations.RunPython(forwards_fill_song_artist, backwards_unfill_song_artist),
		migrations.AlterField(
			model_name='song',
			name='artist',
			field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='songs', to='music.artist'),
		),
	]
