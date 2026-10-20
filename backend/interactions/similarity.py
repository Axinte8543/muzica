from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from math import exp, sqrt

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from .models import AlbumLike, AlbumListen, AlbumRating, AlbumReview, FavoriteAlbum


User = get_user_model()

SIMILARITY_CACHE_VERSION = 4
SIMILAR_USERS_CACHE_TTL = 60 * 60 * 6
COMPATIBILITY_CACHE_TTL = 60 * 60 * 12
MAX_CACHED_SIMILAR_USERS = 50


@dataclass(frozen=True)
class SimilarUser:
    user: User
    similarity: float
    common_ratings: int


def _clamp01(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def _recency_decay(moment, *, half_life_days: float = 180.0) -> float:
    if moment is None:
        return 1.0
    if isinstance(moment, date) and not isinstance(moment, datetime):
        moment = timezone.make_aware(
            datetime.combine(moment, datetime.min.time()),
            timezone.get_current_timezone(),
        )
    elif timezone.is_naive(moment):
        moment = timezone.make_aware(moment, timezone.get_current_timezone())
    age_days = max(0.0, (timezone.now() - moment).total_seconds() / 86400.0)
    if half_life_days <= 0:
        return 1.0
    return exp(-age_days / float(half_life_days))


def _cosine_similarity(left: dict, right: dict) -> float:
    left_keys = set(left.keys())
    right_keys = set(right.keys())
    if not left_keys or not right_keys:
        return 0.0
    common = left_keys & right_keys
    if not common:
        return 0.0
    dot = sum(float(left[key]) * float(right[key]) for key in common)
    norm_left = sqrt(sum(float(value) ** 2 for value in left.values()))
    norm_right = sqrt(sum(float(value) ** 2 for value in right.values()))
    if norm_left <= 0 or norm_right <= 0:
        return 0.0
    return _clamp01(dot / (norm_left * norm_right))


def _euclidean_similarity(left: dict, right: dict) -> float:
    keys = set(left.keys()) | set(right.keys())
    if not keys:
        return 0.0
    distance = sqrt(
        sum((float(left.get(key, 0.0)) - float(right.get(key, 0.0))) ** 2 for key in keys)
    )
    return _clamp01(1.0 / (1.0 + distance))


def _pearson_similarity(left: dict, right: dict) -> float:
    keys = set(left.keys()) & set(right.keys())
    if len(keys) < 2:
        return 0.0
    left_values = [float(left[key]) for key in keys]
    right_values = [float(right[key]) for key in keys]
    mean_left = sum(left_values) / len(left_values)
    mean_right = sum(right_values) / len(right_values)
    numerator = sum((a - mean_left) * (b - mean_right) for a, b in zip(left_values, right_values))
    den_left = sqrt(sum((a - mean_left) ** 2 for a in left_values))
    den_right = sqrt(sum((b - mean_right) ** 2 for b in right_values))
    if den_left <= 0 or den_right <= 0:
        return 0.0
    return max(-1.0, min(1.0, numerator / (den_left * den_right)))


def _jaccard_similarity(left: set[int], right: set[int]) -> float:
    if not left and not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return _clamp01(len(left & right) / len(union))


def _pair_cache_key(user_a_id: int, user_b_id: int) -> str:
    first, second = sorted((int(user_a_id), int(user_b_id)))
    return f"compatibility:v{SIMILARITY_CACHE_VERSION}:pair:{first}:{second}"


def _similar_users_cache_key(user_id: int) -> str:
    return f"compatibility:v{SIMILARITY_CACHE_VERSION}:similar-users:{int(user_id)}"


def _is_compatibility_visible(user: User) -> bool:
    try:
        return bool(getattr(user.privacy, 'public_compatibility', True))
    except Exception:
        return True


def _build_profile(user: User) -> dict:
    genre_weights: dict[int, float] = defaultdict(float)
    artist_weights: dict[int, float] = defaultdict(float)
    album_weights: dict[int, float] = defaultdict(float)
    rating_histogram: dict[int, float] = defaultdict(float)
    ratings_by_album: dict[int, float] = {}
    liked_album_ids: set[int] = set()
    all_album_ids: set[int] = set()

    def add_album_signal(album, weight: float) -> None:
        if album is None:
            return
        album_id = int(album.id)
        if album_id <= 0:
            return
        all_album_ids.add(album_id)
        album_weights[album_id] += float(weight)
        artist_id = int(getattr(album, 'artist_id', 0) or 0)
        if artist_id > 0:
            artist_weights[artist_id] += float(weight)
        for genre in album.genres.all():
            genre_weights[int(genre.id)] += float(weight)

    rating_rows = (
        AlbumRating.objects.select_related('album', 'album__artist')
        .prefetch_related('album__genres')
        .filter(user=user, album__is_approved=True, album__artist__is_approved=True)
    )
    for row in rating_rows:
        album = row.album
        rating = int(row.rating or 0)
        weight = max(0.2, float(rating) / 5.0) * _recency_decay(
            getattr(row, 'created_at', None),
            half_life_days=240.0,
        )
        add_album_signal(album, weight)
        rating_histogram[rating] += weight
        ratings_by_album[int(album.id)] = float(rating)
        if rating >= 4:
            liked_album_ids.add(int(album.id))

    for model, base_weight, half_life_days in (
        (AlbumLike, 1.15, 180.0),
        (FavoriteAlbum, 1.35, 365.0),
        (AlbumReview, 0.9, 210.0),
    ):
        rows = (
            model.objects.select_related('album', 'album__artist')
            .prefetch_related('album__genres')
            .filter(user=user, album__is_approved=True, album__artist__is_approved=True)
        )
        for row in rows:
            album = row.album
            weight = float(base_weight) * _recency_decay(
                getattr(row, 'created_at', None),
                half_life_days=half_life_days,
            )
            add_album_signal(album, weight)
            liked_album_ids.add(int(album.id))

    listen_rows = (
        AlbumListen.objects.select_related('album', 'album__artist')
        .prefetch_related('album__genres')
        .filter(user=user, album__is_approved=True, album__artist__is_approved=True)
    )
    for row in listen_rows:
        album = row.album
        listen_date = getattr(row, 'listened_date', None)
        weight = 0.7 * _recency_decay(listen_date, half_life_days=210.0)
        add_album_signal(album, weight)

    combined_vector = {
        **{f'genre:{key}': float(value) for key, value in genre_weights.items() if float(value) > 0},
        **{f'artist:{key}': float(value) for key, value in artist_weights.items() if float(value) > 0},
        **{f'album:{key}': float(value) for key, value in album_weights.items() if float(value) > 0},
        **{f'rating:{bucket}': float(weight) for bucket, weight in rating_histogram.items() if float(weight) > 0},
    }

    return {
        'genre_weights': dict(genre_weights),
        'artist_weights': dict(artist_weights),
        'album_weights': dict(album_weights),
        'rating_histogram': dict(rating_histogram),
        'ratings_by_album': dict(ratings_by_album),
        'liked_album_ids': set(liked_album_ids),
        'all_album_ids': set(all_album_ids),
        'combined_vector': combined_vector,
    }


def _compatibility_components(user_a: User, user_b: User, *, profile_a: dict | None = None, profile_b: dict | None = None) -> dict:
    profile_a = profile_a or _build_profile(user_a)
    profile_b = profile_b or _build_profile(user_b)

    genre_cosine = _cosine_similarity(profile_a['genre_weights'], profile_b['genre_weights'])
    artist_cosine = _cosine_similarity(profile_a['artist_weights'], profile_b['artist_weights'])
    album_cosine = _cosine_similarity(profile_a['album_weights'], profile_b['album_weights'])
    rating_hist_cosine = _cosine_similarity(profile_a['rating_histogram'], profile_b['rating_histogram'])
    content_score = (genre_cosine + artist_cosine + album_cosine + rating_hist_cosine) / 4.0
    euclidean_score = _euclidean_similarity(profile_a['combined_vector'], profile_b['combined_vector'])
    pearson_raw = _pearson_similarity(profile_a['ratings_by_album'], profile_b['ratings_by_album'])
    pearson_score = (pearson_raw + 1.0) / 2.0
    liked_overlap = _jaccard_similarity(profile_a['liked_album_ids'], profile_b['liked_album_ids'])
    album_overlap = _jaccard_similarity(profile_a['all_album_ids'], profile_b['all_album_ids'])

    score_01 = _clamp01(
        0.30 * content_score
        + 0.25 * euclidean_score
        + 0.25 * pearson_score
        + 0.10 * liked_overlap
        + 0.10 * album_overlap
    )
    common_ratings = len(set(profile_a['ratings_by_album'].keys()) & set(profile_b['ratings_by_album'].keys()))

    return {
        'similarity': round(score_01 * 100.0, 2),
        'common_ratings': int(common_ratings),
    }


def _candidate_user_ids(user: User, profile: dict) -> set[int]:
    shared_album_ids = set(int(album_id) for album_id in profile['all_album_ids'])
    shared_artist_ids = set(int(artist_id) for artist_id in profile['artist_weights'].keys())
    shared_genre_ids = set(int(genre_id) for genre_id in profile['genre_weights'].keys())
    if not shared_album_ids and not shared_artist_ids and not shared_genre_ids:
        return set()

    candidate_ids: set[int] = set()
    for model in (AlbumRating, AlbumLike, FavoriteAlbum, AlbumListen, AlbumReview):
        qs = model.objects.exclude(user=user)
        signal_q = None
        if shared_album_ids:
            signal_q = {'album_id__in': shared_album_ids}
            candidate_ids.update(
                int(user_id)
                for user_id in qs.filter(**signal_q).values_list('user_id', flat=True).distinct()
            )
        if shared_artist_ids:
            candidate_ids.update(
                int(user_id)
                for user_id in qs.filter(album__artist_id__in=shared_artist_ids)
                .values_list('user_id', flat=True)
                .distinct()
            )
        if shared_genre_ids:
            candidate_ids.update(
                int(user_id)
                for user_id in qs.filter(album__genres__id__in=shared_genre_ids)
                .values_list('user_id', flat=True)
                .distinct()
            )
    candidate_ids.discard(int(user.id))
    return candidate_ids


def _serialize_similar_user(user: User, similarity_value: float, common_ratings: int) -> dict:
    return {
        'user_id': int(user.id),
        'username': user.username,
        'similarity': round(float(similarity_value), 2),
        'common_ratings': int(common_ratings),
    }


def _cached_similar_users_to_objects(cached_rows: list[dict], *, limit: int) -> list[SimilarUser]:
    if not cached_rows:
        return []
    user_ids = [int(row.get('user_id')) for row in cached_rows if row.get('user_id') is not None]
    users_by_id = {u.id: u for u in User.objects.select_related('privacy').filter(id__in=user_ids)}
    results: list[SimilarUser] = []
    for row in cached_rows:
        user_id = row.get('user_id')
        if user_id is None:
            continue
        user = users_by_id.get(int(user_id))
        if user is None or not _is_compatibility_visible(user):
            continue
        results.append(
            SimilarUser(
                user=user,
                similarity=float(row.get('similarity') or 0.0),
                common_ratings=int(row.get('common_ratings') or 0),
            )
        )
    if limit and limit > 0:
        results = results[:limit]
    return results


def common_taste_details(
    user_a: User,
    user_b: User,
    *,
    max_genres: int = 3,
    max_artists: int = 3,
    max_albums: int = 2,
    min_like_rating: int = 4,
) -> dict:
\
\
\
\
       
    from music.models import Album, Artist, Genre

    qs_a = AlbumRating.objects.filter(
        user=user_a,
        rating__gte=min_like_rating,
        album__is_approved=True,
        album__artist__is_approved=True,
    )
    qs_b = AlbumRating.objects.filter(
        user=user_b,
        rating__gte=min_like_rating,
        album__is_approved=True,
        album__artist__is_approved=True,
    )

    liked_album_ids_a = set(qs_a.values_list('album_id', flat=True).distinct())
    liked_album_ids_b = set(qs_b.values_list('album_id', flat=True).distinct())
    common_album_ids = liked_album_ids_a.intersection(liked_album_ids_b)

    artist_ids_a = set(qs_a.values_list('album__artist_id', flat=True).distinct())
    artist_ids_b = set(qs_b.values_list('album__artist_id', flat=True).distinct())
    common_artist_ids = artist_ids_a.intersection(artist_ids_b)

    genre_ids_a = set(
        gid
        for gid in qs_a.values_list('album__genres__id', flat=True).distinct()
        if gid
    )
    genre_ids_b = set(
        gid
        for gid in qs_b.values_list('album__genres__id', flat=True).distinct()
        if gid
    )
    common_genre_ids = genre_ids_a.intersection(genre_ids_b)

    common_genres = list(
        Genre.objects.filter(id__in=common_genre_ids).order_by('name').values_list('name', flat=True)[:max_genres]
    )
    common_artists = list(
        Artist.objects.filter(is_approved=True, id__in=common_artist_ids)
        .order_by('name')
        .values_list('name', flat=True)[:max_artists]
    )
    common_albums = list(
        Album.objects.filter(is_approved=True, artist__is_approved=True, id__in=common_album_ids)
        .order_by('title')
        .values_list('title', flat=True)[:max_albums]
    )

    return {
        "common_genres": common_genres,
        "common_artists": common_artists,
        "common_albums": common_albums,
    }


def _compatibility_payload_internal(user_a: User, user_b: User) -> dict:
    components = _compatibility_components(user_a, user_b)
    return {
        'user_id': int(user_b.id),
        'username': user_b.username,
        'similarity': float(components['similarity']),
        **common_taste_details(user_a, user_b),
    }


def similarity(user_a: User, user_b: User) -> float:
    cache_key = _pair_cache_key(user_a.id, user_b.id)
    cached = cache.get(cache_key)
    if isinstance(cached, dict) and 'similarity' in cached:
        return float(cached['similarity'])
    payload = _compatibility_payload_internal(user_a, user_b)
    cache.set(cache_key, payload, COMPATIBILITY_CACHE_TTL)
    return float(payload['similarity'])


def similar_users_for(user: User, *, limit: int = 10) -> list[SimilarUser]:
    cache_key = _similar_users_cache_key(user.id)
    cached = cache.get(cache_key)
    if isinstance(cached, list):
        return _cached_similar_users_to_objects(cached, limit=limit)

    profile_a = _build_profile(user)
    if not profile_a['all_album_ids']:
        cache.set(cache_key, [], SIMILAR_USERS_CACHE_TTL)
        return []

    candidate_ids = _candidate_user_ids(user, profile_a)
    if not candidate_ids:
        cache.set(cache_key, [], SIMILAR_USERS_CACHE_TTL)
        return []

    users = list(User.objects.select_related('privacy').filter(id__in=candidate_ids))
    results: list[SimilarUser] = []
    for other in users:
        if other.id == user.id or not _is_compatibility_visible(other):
            continue
        profile_b = _build_profile(other)
        if not profile_b['all_album_ids']:
            continue
        components = _compatibility_components(user, other, profile_a=profile_a, profile_b=profile_b)
        if components['similarity'] <= 0:
            continue
        results.append(
            SimilarUser(
                user=other,
                similarity=float(components['similarity']),
                common_ratings=int(components['common_ratings']),
            )
        )

    results.sort(key=lambda item: (-float(item.similarity), -int(item.common_ratings), item.user.username))
    cache.set(
        cache_key,
        [
            _serialize_similar_user(item.user, item.similarity, item.common_ratings)
            for item in results[:MAX_CACHED_SIMILAR_USERS]
        ],
        SIMILAR_USERS_CACHE_TTL,
    )
    if limit and limit > 0:
        results = results[:limit]
    return results


def compute_and_cache_similar_users(user_id: int, *, limit: int = MAX_CACHED_SIMILAR_USERS) -> list[dict]:
    user = User.objects.select_related('privacy').filter(id=user_id).first()
    if user is None:
        cache.delete(_similar_users_cache_key(user_id))
        return []
    results = similar_users_for(user, limit=limit)
    payload = [_serialize_similar_user(item.user, item.similarity, item.common_ratings) for item in results]
    cache.set(_similar_users_cache_key(user.id), payload, SIMILAR_USERS_CACHE_TTL)
    return payload


def compatibility_payload(user_a: User, user_b: User) -> dict:
                                                 
    cache_key = _pair_cache_key(user_a.id, user_b.id)
    cached = cache.get(cache_key)
    if isinstance(cached, dict) and 'similarity' in cached:
        return cached
    payload = _compatibility_payload_internal(user_a, user_b)
    cache.set(cache_key, payload, COMPATIBILITY_CACHE_TTL)
    return payload
