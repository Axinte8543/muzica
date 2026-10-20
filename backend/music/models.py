from django.db import models


class Genre(models.Model):
	name = models.CharField(max_length=100, unique=True)
	slug = models.SlugField(max_length=255, unique=True)

	def __str__(self):
		return self.name


class Artist(models.Model):
	name = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255, unique=True)
	bio = models.TextField(blank=True)
	image_url = models.URLField(blank=True)
	musicbrainz_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
	spotify_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
	spotify_url = models.URLField(blank=True)
	popularity = models.PositiveIntegerField(null=True, blank=True)
	is_romanian = models.BooleanField(default=True)
	aliases = models.TextField(blank=True, help_text="Separate by commas")
	is_approved = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	genres = models.ManyToManyField(Genre, blank=True, related_name='artists')

	def __str__(self):
		return self.name


class Album(models.Model):
	artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='albums')
	title = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255, unique=True)
	description = models.TextField(blank=True)
	cover_url = models.URLField(blank=True)
	musicbrainz_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
	spotify_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
	spotify_url = models.URLField(blank=True)
                                                                                      
	mb_primary_type = models.CharField(max_length=32, blank=True, db_index=True)
	mb_secondary_types = models.TextField(blank=True, help_text="Comma-separated MusicBrainz secondary types")
	release_date = models.DateField()
	is_approved = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	genres = models.ManyToManyField(Genre, blank=True, related_name='albums')

	def __str__(self):
		return self.title


class Song(models.Model):
                                                                   
	album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='songs', null=True, blank=True)
	artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='songs')
	title = models.CharField(max_length=255)
	slug = models.SlugField(max_length=255, unique=True)
	musicbrainz_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
	spotify_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
	spotify_url = models.URLField(blank=True)
	preview_url = models.URLField(blank=True)
	popularity = models.PositiveIntegerField(null=True, blank=True)
	track_number = models.PositiveIntegerField(null=True, blank=True)
	duration_seconds = models.PositiveIntegerField(default=0)
	description = models.TextField(blank=True)
	is_approved = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	genres = models.ManyToManyField(Genre, blank=True, related_name='songs')

	class Meta:
		ordering = ['track_number']

	def __str__(self):
		if self.track_number is None:
			return self.title
		return f"{self.track_number}. {self.title}"


class SongFeature(models.Model):
                                                                   

	song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='features')
	artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='featured_on_songs')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
		 models.UniqueConstraint(fields=['song', 'artist'], name='unique_song_feature_per_song_artist'),
		]
		indexes = [
		 models.Index(fields=['song', '-created_at'], name='sf_song_created_idx'),
		 models.Index(fields=['artist', '-created_at'], name='sf_artist_created_idx'),
		]
		ordering = ['-created_at', '-id']

	def __str__(self) -> str:
		return f"{self.song} feat. {self.artist}"


class ArtistSimilarity(models.Model):
	from_artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='similar_artists')
	to_artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='similar_to')
	source = models.CharField(max_length=32, default='lastfm')
	match = models.FloatField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
		 models.UniqueConstraint(fields=['from_artist', 'to_artist', 'source'], name='unique_artist_similarity_edge'),
		]

	def __str__(self) -> str:
		return f"{self.from_artist} -> {self.to_artist} ({self.source})"
