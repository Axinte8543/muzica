from rest_framework import serializers
from django.utils.text import slugify

from .models import Album, Artist, Genre, Song


class SafeReleaseDateField(serializers.DateField):
    def to_representation(self, value):
        if value and getattr(value, "year", None) == 1970:
            return None
        return super().to_representation(value)


def _generate_unique_slug(*, model, base: str) -> str:
    base_slug = slugify(str(base))
    if not base_slug:
        base_slug = 'item'

    slug = base_slug
    suffix = 2
    while model.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


def _resolve_approved_artist(raw: str):
    value = str(raw or '').strip()
    if not value:
        return None

    slug_value = slugify(value)
    artist = (
        Artist.objects
        .filter(is_approved=True, slug__iexact=value)
        .first()
    )
    if artist:
        return artist

    if slug_value:
        artist = (
            Artist.objects
            .filter(is_approved=True, slug__iexact=slug_value)
            .first()
        )
        if artist:
            return artist

    artist = (
        Artist.objects
        .filter(is_approved=True, name__iexact=value)
        .first()
    )
    if artist:
        return artist

    normalized = value.casefold()
    for candidate in Artist.objects.filter(is_approved=True, aliases__icontains=value):
        aliases = [
            part.strip().casefold()
            for part in str(candidate.aliases or '').split(',')
            if part.strip()
        ]
        if normalized in aliases:
            return candidate

    return None


def _resolve_approved_album(raw: str, *, artist: Artist):
    value = str(raw or '').strip()
    if not value:
        return None

    slug_value = slugify(value)
    qs = Album.objects.filter(
        is_approved=True,
        artist=artist,
        artist__is_approved=True,
    )

    album = qs.filter(slug__iexact=value).select_related('artist').first()
    if album:
        return album
    if slug_value:
        album = qs.filter(slug__iexact=slug_value).select_related('artist').first()
        if album:
            return album
    return qs.filter(title__iexact=value).select_related('artist').first()


def _album_songs_count(obj) -> int:
    annotated = getattr(obj, 'songs_count', None)
    if annotated is not None:
        try:
            return int(annotated)
        except (TypeError, ValueError):
            pass
    songs = getattr(obj, 'songs', None)
    if songs is None:
        return 0
    try:
        return int(songs.count())
    except Exception:
        return 0


def album_release_type(obj) -> str:
    primary = str(getattr(obj, 'mb_primary_type', '') or '').strip().lower()
    songs_count = _album_songs_count(obj)
    if primary == 'single' or songs_count == 1:
        return 'single'
    if primary in {'album', 'ep', 'compilation'}:
        return primary
    return 'album'


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name', 'slug']


class SongSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    genres = GenreSerializer(many=True, read_only=True)
    artist_slug = serializers.SlugField(source='artist.slug', read_only=True)
    album_title = serializers.CharField(source='album.title', read_only=True)
    album_slug = serializers.SlugField(source='album.slug', read_only=True)
    album_cover_url = serializers.CharField(source='album.cover_url', read_only=True, allow_null=True)
    album_release_type = serializers.SerializerMethodField()
    album_songs_count = serializers.SerializerMethodField()
    genres = GenreSerializer(many=True, read_only=True)
    featured_artists = serializers.SerializerMethodField()

    def get_album_release_type(self, obj):
        album = getattr(obj, 'album', None)
        if not album:
            return ''
        return album_release_type(album)

    def get_album_songs_count(self, obj):
        album = getattr(obj, 'album', None)
        if not album:
            return 0
        return _album_songs_count(album)

    def get_featured_artists(self, obj):
        features = getattr(obj, 'features', None)
        if not features:
            return []
                                                                              
        out = []
        for f in features.all():
            artist = getattr(f, 'artist', None)
            if not artist:
                continue
            out.append({
                'id': int(artist.id),
                'name': artist.name,
                'slug': artist.slug,
            })
        return out

    class Meta:
        model = Song
        fields = [
            'id',
            'title',
            'slug',
            'spotify_url',
            'preview_url',
            'popularity',
            'track_number',
            'duration_seconds',
            'description',
            'artist_name',
            'artist_slug',
            'featured_artists',
            'album_title',
            'album_slug',
            'album_cover_url',
            'album_release_type',
            'album_songs_count',
            'genres',
        ]


class SongInAlbumSerializer(SongSerializer):
    average_rating = serializers.FloatField(read_only=True, allow_null=True)
    ratings_count = serializers.IntegerField(read_only=True)
    my_rating = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta(SongSerializer.Meta):
        fields = SongSerializer.Meta.fields + [
            'average_rating',
            'ratings_count',
            'my_rating',
        ]


class AlbumListSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    genres = GenreSerializer(many=True, read_only=True)
    release_date = SafeReleaseDateField(read_only=True)
    mb_primary_type = serializers.CharField(read_only=True)
    songs_count = serializers.SerializerMethodField()
    release_type = serializers.SerializerMethodField()

    def get_songs_count(self, obj):
        return _album_songs_count(obj)

    def get_release_type(self, obj):
        return album_release_type(obj)

    class Meta:
        model = Album
        fields = [
            'id',
            'title',
            'slug',
            'cover_url',
            'spotify_url',
            'release_date',
            'artist_name',
            'mb_primary_type',
            'songs_count',
            'release_type',
            'genres',
        ]


class AlbumDetailSerializer(serializers.ModelSerializer):
    artist = serializers.StringRelatedField()
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    artist_slug = serializers.SlugField(source='artist.slug', read_only=True)
    genres = GenreSerializer(many=True, read_only=True)
    songs = SongInAlbumSerializer(many=True, read_only=True)
    release_date = SafeReleaseDateField(read_only=True)
    mb_primary_type = serializers.CharField(read_only=True)
    mb_secondary_types = serializers.CharField(read_only=True)
    songs_count = serializers.SerializerMethodField()
    release_type = serializers.SerializerMethodField()

    average_rating = serializers.FloatField(read_only=True, allow_null=True)
    ratings_count = serializers.IntegerField(read_only=True)

    def get_songs_count(self, obj):
        return _album_songs_count(obj)

    def get_release_type(self, obj):
        return album_release_type(obj)

    class Meta:
        model = Album
        fields = [
            'id',
            'title',
            'slug',
            'description',
            'cover_url',
            'spotify_url',
            'release_date',
            'mb_primary_type',
            'mb_secondary_types',
            'songs_count',
            'release_type',
            'artist',
            'artist_name',
            'artist_slug',
            'genres',
            'average_rating',
            'ratings_count',
            'songs',
        ]


class AlbumInArtistSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    average_rating = serializers.FloatField(read_only=True, allow_null=True)
    ratings_count = serializers.IntegerField(read_only=True)
    mb_primary_type = serializers.CharField(read_only=True)
    mb_secondary_types = serializers.CharField(read_only=True)
    release_date = SafeReleaseDateField(read_only=True)

    class Meta:
        model = Album
        fields = [
            'id',
            'title',
            'slug',
            'cover_url',
            'spotify_url',
            'mb_primary_type',
            'mb_secondary_types',
            'release_date',
            'genres',
            'average_rating',
            'ratings_count',
        ]


class SongInArtistSerializer(serializers.ModelSerializer):
    album_title = serializers.CharField(source='album.title', read_only=True)
    album_slug = serializers.SlugField(source='album.slug', read_only=True)
    genres = GenreSerializer(many=True, read_only=True)
    average_rating = serializers.FloatField(read_only=True, allow_null=True)
    ratings_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Song
        fields = [
            'id',
            'title',
            'slug',
            'spotify_url',
            'preview_url',
            'popularity',
            'track_number',
            'duration_seconds',
            'description',
            'album_title',
            'album_slug',
            'genres',
            'average_rating',
            'ratings_count',
        ]


class ArtistDetailSerializer(serializers.ModelSerializer):
    albums_count = serializers.IntegerField(read_only=True)
    songs_count = serializers.IntegerField(read_only=True)
    followers_count = serializers.IntegerField(read_only=True)
    average_rating = serializers.FloatField(read_only=True, allow_null=True)
    ratings_count = serializers.IntegerField(read_only=True)
    genres = GenreSerializer(many=True, read_only=True)
    albums = AlbumInArtistSerializer(many=True, read_only=True)
    songs = SongInArtistSerializer(many=True, read_only=True)

    class Meta:
        model = Artist
        fields = [
            'id',
            'name',
            'slug',
            'bio',
            'image_url',
            'musicbrainz_id',
            'spotify_id',
            'spotify_url',
            'popularity',
            'is_romanian',
            'aliases',
            'genres',
            'albums_count',
            'songs_count',
            'followers_count',
            'average_rating',
            'ratings_count',
            'albums',
            'songs',
        ]


class SimilarArtistSerializer(serializers.ModelSerializer):
    match = serializers.FloatField(read_only=True, allow_null=True)

    class Meta:
        model = Artist
        fields = [
            'id',
            'name',
            'slug',
            'image_url',
            'match',
        ]


class SearchArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = [
            'id',
            'name',
            'slug',
        ]


class RandomArtistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = [
            'id',
            'name',
            'slug',
            'image_url',
        ]


class SearchAlbumSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    artist_slug = serializers.SlugField(source='artist.slug', read_only=True)
    mb_primary_type = serializers.CharField(read_only=True)
    songs_count = serializers.SerializerMethodField()
    release_type = serializers.SerializerMethodField()

    def get_songs_count(self, obj):
        return _album_songs_count(obj)

    def get_release_type(self, obj):
        return album_release_type(obj)

    class Meta:
        model = Album
        fields = [
            'id',
            'title',
            'slug',
            'artist_name',
            'artist_slug',
            'mb_primary_type',
            'songs_count',
            'release_type',
        ]


class SearchSongSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    artist_slug = serializers.SlugField(source='artist.slug', read_only=True)
    album_title = serializers.CharField(source='album.title', read_only=True)
    album_slug = serializers.SlugField(source='album.slug', read_only=True)
    album_release_type = serializers.SerializerMethodField()

    def get_album_release_type(self, obj):
        album = getattr(obj, 'album', None)
        if not album:
            return ''
        return album_release_type(album)

    class Meta:
        model = Song
        fields = [
            'id',
            'title',
            'slug',
            'artist_name',
            'artist_slug',
            'album_title',
            'album_slug',
            'album_release_type',
        ]


class TopAlbumSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    artist_slug = serializers.SlugField(source='artist.slug', read_only=True)
    average_rating = serializers.FloatField(read_only=True, allow_null=True)
    ratings_count = serializers.IntegerField(read_only=True)
    release_date = SafeReleaseDateField(read_only=True)
    mb_primary_type = serializers.CharField(read_only=True)
    songs_count = serializers.SerializerMethodField()
    release_type = serializers.SerializerMethodField()

    def get_songs_count(self, obj):
        return _album_songs_count(obj)

    def get_release_type(self, obj):
        return album_release_type(obj)

    class Meta:
        model = Album
        fields = [
            'id',
            'title',
            'slug',
            'cover_url',
            'release_date',
            'artist_name',
            'artist_slug',
            'average_rating',
            'ratings_count',
            'mb_primary_type',
            'songs_count',
            'release_type',
        ]


class TopArtistSerializer(serializers.ModelSerializer):
    average_rating = serializers.FloatField(read_only=True, allow_null=True)
    ratings_count = serializers.IntegerField(read_only=True)
    albums_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Artist
        fields = [
            'id',
            'name',
            'slug',
            'image_url',
            'average_rating',
            'ratings_count',
            'albums_count',
        ]


class ListenedAlbumSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    artist_slug = serializers.SlugField(source='artist.slug', read_only=True)
    average_rating = serializers.FloatField(read_only=True, allow_null=True)
    ratings_count = serializers.IntegerField(read_only=True)
    listens_count = serializers.IntegerField(read_only=True)
    release_date = SafeReleaseDateField(read_only=True)

    class Meta:
        model = Album
        fields = [
            'id',
            'title',
            'slug',
            'cover_url',
            'release_date',
            'artist_name',
            'artist_slug',
            'average_rating',
            'ratings_count',
            'listens_count',
        ]


class AnticipatedAlbumSerializer(serializers.ModelSerializer):
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    artist_slug = serializers.SlugField(source='artist.slug', read_only=True)
    ratings_count = serializers.IntegerField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)
    interest_score = serializers.IntegerField(read_only=True)
    release_date = SafeReleaseDateField(read_only=True)

    class Meta:
        model = Album
        fields = [
            'id',
            'title',
            'slug',
            'cover_url',
            'release_date',
            'artist_name',
            'artist_slug',
            'ratings_count',
            'reviews_count',
            'interest_score',
        ]


class RecommendationSerializer(serializers.Serializer):

    album = serializers.CharField()
    artist = serializers.CharField()
    album_id = serializers.IntegerField(required=False)
    album_slug = serializers.CharField(required=False, allow_blank=True)
    cover_url = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)
    genre_score = serializers.FloatField(required=False)
    similar_users_score = serializers.FloatField(required=False)
    popularity_score = serializers.FloatField(required=False)
    artist_slug = serializers.CharField(required=False, allow_blank=True)
    score = serializers.FloatField()


class TrendingAlbumSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    slug = serializers.CharField()
    cover_url = serializers.CharField(allow_blank=True, required=False)
    release_date = SafeReleaseDateField(required=False)
    artist_name = serializers.CharField()
    artist_slug = serializers.CharField()

    current_score = serializers.IntegerField()
    previous_score = serializers.IntegerField()
    delta = serializers.IntegerField()


class TrendingArtistSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()
    image_url = serializers.CharField(allow_blank=True, required=False)

    current_score = serializers.IntegerField()
    previous_score = serializers.IntegerField()
    delta = serializers.IntegerField()


class MostDiscussedAlbumSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    slug = serializers.CharField()
    cover_url = serializers.CharField(allow_blank=True, required=False)
    release_date = SafeReleaseDateField(required=False)
    artist_name = serializers.CharField()
    artist_slug = serializers.CharField()

    discussions_count = serializers.IntegerField()


class ArtistSuggestSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Artist
        fields = [
            'id',
            'name',
            'slug',
            'bio',
            'image_url',
            'aliases',
        ]
        read_only_fields = ['id']

    def validate_name(self, value: str):
        name = str(value).strip()
        if not name:
            raise serializers.ValidationError('Name is required')
        return name

    def validate_slug(self, value: str):
        return str(value).strip()

    def create(self, validated_data):
        slug_raw = validated_data.pop('slug', '')
        base = slug_raw or validated_data.get('name', '')
        validated_data['slug'] = _generate_unique_slug(model=Artist, base=base)
        validated_data['is_approved'] = False
        return Artist.objects.create(**validated_data)


class AlbumSuggestSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(required=False, allow_blank=True)
    artist_slug = serializers.CharField(write_only=True)

    class Meta:
        model = Album
        fields = [
            'id',
            'title',
            'slug',
            'description',
            'cover_url',
            'release_date',
            'artist_slug',
        ]
        read_only_fields = ['id']

    def validate_title(self, value: str):
        title = str(value).strip()
        if not title:
            raise serializers.ValidationError('Title is required')
        return title

    def validate_slug(self, value: str):
        return str(value).strip()

    def validate_artist_slug(self, value: str):
        artist_ref = str(value).strip()
        if not artist_ref:
            raise serializers.ValidationError('artist_slug is required')
        return artist_ref

    def create(self, validated_data):
        artist_ref = validated_data.pop('artist_slug')
        artist = _resolve_approved_artist(artist_ref)
        if not artist:
            raise serializers.ValidationError({'artist_slug': 'Artist not found or not approved'})

        slug_raw = validated_data.pop('slug', '')
        base = slug_raw or validated_data.get('title', '')
        validated_data['slug'] = _generate_unique_slug(model=Album, base=base)
        validated_data['artist'] = artist
        validated_data['is_approved'] = False
        return Album.objects.create(**validated_data)


class SongSuggestSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(required=False, allow_blank=True)
    artist_slug = serializers.CharField(write_only=True)
    album_slug = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Song
        fields = [
            'id',
            'title',
            'slug',
            'track_number',
            'duration_seconds',
            'description',
            'artist_slug',
            'album_slug',
        ]
        read_only_fields = ['id']

    def validate_title(self, value: str):
        title = str(value).strip()
        if not title:
            raise serializers.ValidationError('Title is required')
        return title

    def validate_slug(self, value: str):
        return str(value).strip()

    def validate_artist_slug(self, value: str):
        artist_ref = str(value).strip()
        if not artist_ref:
            raise serializers.ValidationError('artist_slug is required')
        return artist_ref

    def validate_album_slug(self, value):
        if value is None:
            return None
        slug = str(value).strip()
        return slug or None

    def create(self, validated_data):
        artist_ref = validated_data.pop('artist_slug')
        album_ref = validated_data.pop('album_slug', None)

        artist = _resolve_approved_artist(artist_ref)
        if not artist:
            raise serializers.ValidationError({'artist_slug': 'Artist not found or not approved'})

        album = None
        if album_ref:
            album = _resolve_approved_album(album_ref, artist=artist)
            if not album:
                raise serializers.ValidationError({'album_slug': 'Album not found or not approved'})

        slug_raw = validated_data.pop('slug', '')
        base = slug_raw or validated_data.get('title', '')
        validated_data['slug'] = _generate_unique_slug(model=Song, base=base)
        validated_data['artist'] = artist
        validated_data['album'] = album
        validated_data['is_approved'] = False
        return Song.objects.create(**validated_data)
