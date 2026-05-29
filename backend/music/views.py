from collections import defaultdict

from django.db.models import Avg, Count, Exists, F, FloatField, IntegerField, OuterRef, Prefetch, Q, Subquery, Value
from django.db.models.expressions import ExpressionWrapper
from django.db.models.functions import Coalesce, Abs
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import date, timedelta
import random
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.cache import cache

from .models import Album, Artist, ArtistSimilarity, Genre, Song, SongFeature
from .pagination import AlbumPagination
from .serializers import (
	AlbumDetailSerializer,
	AlbumInArtistSerializer,
	AlbumListSerializer,
	ArtistDetailSerializer,
	AlbumSuggestSerializer,
	ArtistSuggestSerializer,
	GenreSerializer,
	SimilarArtistSerializer,
	SearchAlbumSerializer,
	SearchArtistSerializer,
	SearchSongSerializer,
	SongInArtistSerializer,
	SongSerializer,
	SongSuggestSerializer,
	AnticipatedAlbumSerializer,
	ListenedAlbumSerializer,
	TopAlbumSerializer,
	TopArtistSerializer,
	RandomArtistSerializer,
	RecommendationSerializer,
	TrendingAlbumSerializer,
	TrendingArtistSerializer,
	MostDiscussedAlbumSerializer,
)

from interactions.models import (
	AlbumListen,
	AlbumRating,
	AlbumLike,
	AlbumReview,
	AlbumReviewLike,
	ArtistFollow,
	CatalogChangelogEvent,
	FriendRequest,
	FavoriteAlbum,
	List,
	ListAlbum,
	ListLike,
	ReviewComment,
	SongRating,
	UserActivity,
)
from interactions.similarity import similar_users_for
from interactions.serializers import (
	CatalogChangelogEventSerializer,
	PopularAlbumReviewSerializer,
	PublicListSerializer,
	ReviewCommentSerializer,
	UserActivitySerializer,
)


class AlbumChangelogView(APIView):
	permission_classes = [AllowAny]

	def get(self, request, slug: str):
		album = get_object_or_404(
			Album.objects.select_related('artist'),
			slug=slug,
			is_approved=True,
			artist__is_approved=True,
		)
		events = (
			CatalogChangelogEvent.objects.select_related('actor')
			.filter(album=album)
			.order_by('-created_at', '-id')[:50]
		)
		return Response(CatalogChangelogEventSerializer(events, many=True).data)


class ArtistChangelogView(APIView):
	permission_classes = [AllowAny]

	def get(self, request, slug: str):
		artist = get_object_or_404(
			Artist.objects.all(),
			slug=slug,
			is_approved=True,
		)
		events = (
			CatalogChangelogEvent.objects.select_related('actor')
			.filter(artist=artist)
			.order_by('-created_at', '-id')[:50]
		)
		return Response(CatalogChangelogEventSerializer(events, many=True).data)


def _parse_limit(raw: str, *, default: int, max_value: int) -> int:
	raw_s = str(raw or '').strip()
	try:
		limit = int(raw_s) if raw_s else int(default)
	except ValueError:
		limit = int(default)
	return max(1, min(int(limit), int(max_value)))


def _merge_recommendation_payloads(
	primary: list[dict],
	secondary: list[dict],
	limit: int,
	excluded_album_ids: set[int] | None = None,
) -> list[dict]:
	merged: dict[int, dict] = {}
	excluded_album_ids = {int(album_id) for album_id in (excluded_album_ids or set())}

	for payloads in (primary, secondary):
		for item in payloads:
			album_id = item.get('album_id')
			if album_id is None:
				continue
			album_id = int(album_id)
			if album_id in excluded_album_ids:
				continue
			score = float(item.get('score') or 0.0)
			existing = merged.get(album_id)
			if existing is None:
				merged[album_id] = dict(item)
				merged[album_id]['score'] = round(score, 2)
				continue

			existing_score = float(existing.get('score') or 0.0)
			if existing_score > 0 and score > 0:
				existing['score'] = round(min(1.0, (existing_score + score) / 2.0), 2)
			elif score > existing_score:
				existing['score'] = round(score, 2)

			if not str(existing.get('reason') or '').strip() and str(item.get('reason') or '').strip():
				existing['reason'] = item.get('reason')

	ordered = sorted(
		merged.values(),
		key=lambda r: (-float(r.get('score') or 0.0), -float(r.get('popularity_score') or 0.0), str(r.get('album') or '')),
	)
	return ordered[:limit]


def _user_signal_album_ids(user) -> set[int]:
	album_ids: set[int] = set()
	for qs in [
		AlbumRating.objects.filter(user=user, rating__gte=4).values_list('album_id', flat=True),
		AlbumListen.objects.filter(user=user).values_list('album_id', flat=True),
		FavoriteAlbum.objects.filter(user=user).values_list('album_id', flat=True),
		AlbumLike.objects.filter(user=user).values_list('album_id', flat=True),
		AlbumReview.objects.filter(user=user).values_list('album_id', flat=True),
		AlbumReviewLike.objects.filter(user=user).values_list('review__album_id', flat=True),
	]:
		for album_id in qs:
			if album_id is not None:
				album_ids.add(int(album_id))
	return album_ids

def _activity_signal_weights_for_user(user) -> tuple[dict[int, float], dict[int, float]]:
	"""Translate recent user activity feed items into album and artist signal weights."""
	album_weights: dict[int, float] = defaultdict(float)
	artist_weights: dict[int, float] = defaultdict(float)

	recent_activities = (
		UserActivity.objects.filter(actor=user)
		.order_by('-created_at', '-id')[:200]
	)
	for activity in recent_activities:
		activity_type = str(activity.activity_type or '')
		target_id = activity.target_id
		if target_id is None:
			continue

		if activity_type == UserActivity.Type.LISTEN_ALBUM:
			album_weights[int(target_id)] += 1.0
		elif activity_type == UserActivity.Type.RATE_ALBUM:
			rating = float(activity.rating or 0.0)
			album_weights[int(target_id)] += max(0.0, rating / 5.0) * 3.0
		elif activity_type == UserActivity.Type.REVIEW_ALBUM:
			album_weights[int(target_id)] += 2.0
		elif activity_type == UserActivity.Type.FOLLOW_ARTIST:
			artist_weights[int(target_id)] += 3.0
		elif activity_type == UserActivity.Type.LIST_ADD_ALBUM:
			album_weights[int(target_id)] += 1.5

	return album_weights, artist_weights


def _recommendations_payload(*, user, limit: int, exclude_in_lists: bool):
	seed_sources = [
		(AlbumRating.objects.filter(user=user, rating__gte=4).values_list('album_id', flat=True), 3.0),
		(AlbumListen.objects.filter(user=user).values_list('album_id', flat=True), 1.0),
		(FavoriteAlbum.objects.filter(user=user).values_list('album_id', flat=True), 4.0),
		(AlbumLike.objects.filter(user=user).values_list('album_id', flat=True), 2.5),
		(AlbumReview.objects.filter(user=user).values_list('album_id', flat=True), 2.0),
		(AlbumReviewLike.objects.filter(user=user).values_list('review__album_id', flat=True), 1.5),
	]

	seed_album_weights: dict[int, float] = defaultdict(float)
	has_any_signal = False
	for qs, weight in seed_sources:
		album_ids = [int(aid) for aid in qs if aid is not None]
		if album_ids:
			has_any_signal = True
		for album_id in album_ids:
			seed_album_weights[album_id] += float(weight)

	activity_album_weights, activity_artist_weights = _activity_signal_weights_for_user(user)
	if activity_album_weights or activity_artist_weights:
		has_any_signal = True
	for album_id, weight in activity_album_weights.items():
		seed_album_weights[int(album_id)] += float(weight)

	followed_artist_ids = set(ArtistFollow.objects.filter(user=user).values_list('artist_id', flat=True))
	if followed_artist_ids:
		has_any_signal = True

	similar = similar_users_for(user, limit=20)
	similar_user_weight_by_id = {su.user.id: float(su.similarity) / 100.0 for su in similar}
	similar_user_ids = list(similar_user_weight_by_id.keys())
	if similar_user_ids:
		has_any_signal = True

	friend_ids = list(_friend_ids_for_user(user))
	friend_album_weights: dict[int, float] = defaultdict(float)
	if friend_ids:
		has_any_signal = True
		friend_rating_rows = (
			AlbumRating.objects.filter(
				user_id__in=friend_ids,
				rating__gte=4,
				album__is_approved=True,
				album__artist__is_approved=True,
			)
			.values('album_id')
			.annotate(friend_ratings=Count('id'), friend_users=Count('user_id', distinct=True), friend_avg=Avg('rating'))
		)
		for row in friend_rating_rows:
			album_id = int(row['album_id'])
			friend_album_weights[album_id] += float(row.get('friend_ratings', 0) or 0) * 1.25
			friend_album_weights[album_id] += float(row.get('friend_users', 0) or 0) * 0.75
			friend_album_weights[album_id] += float(row.get('friend_avg', 0.0) or 0.0) / 5.0

		friend_review_rows = (
			AlbumReview.objects.filter(
				user_id__in=friend_ids,
				album__is_approved=True,
				album__artist__is_approved=True,
			)
			.values('album_id')
			.annotate(friend_reviews=Count('id'), friend_reviewers=Count('user_id', distinct=True))
		)
		for row in friend_review_rows:
			album_id = int(row['album_id'])
			friend_album_weights[album_id] += float(row.get('friend_reviews', 0) or 0) * 0.9
			friend_album_weights[album_id] += float(row.get('friend_reviewers', 0) or 0) * 0.6

	if not has_any_signal:
		return []

	seed_album_ids = list(seed_album_weights.keys())
	seed_albums = (
		Album.objects.select_related('artist')
		.prefetch_related('genres')
		.filter(id__in=seed_album_ids, is_approved=True, artist__is_approved=True)
	)

	favorite_genre_weights: dict[int, float] = defaultdict(float)
	favorite_artist_weights: dict[int, float] = defaultdict(float)
	for album in seed_albums:
		weight = float(seed_album_weights.get(int(album.id), 0.0) or 0.0)
		if weight <= 0:
			continue
		favorite_artist_weights[int(album.artist_id)] += weight
		for genre in album.genres.all():
			favorite_genre_weights[int(genre.id)] += weight

	for artist_id in followed_artist_ids:
		favorite_artist_weights[int(artist_id)] += 3.0
	for artist_id, weight in activity_artist_weights.items():
		favorite_artist_weights[int(artist_id)] += float(weight)

	max_genre_weight = max(favorite_genre_weights.values(), default=0.0)
	max_artist_weight = max(favorite_artist_weights.values(), default=0.0)
	max_friend_weight = max(friend_album_weights.values(), default=0.0)

	rated_album_ids = AlbumRating.objects.filter(user=user).values_list('album_id', flat=True)
	excluded_album_ids = set(seed_album_weights.keys())
	if exclude_in_lists:
		list_album_ids = ListAlbum.objects.filter(list__user=user).values_list('album_id', flat=True)
		excluded_album_ids.update(list_album_ids)

	signal_genre_ids = list(favorite_genre_weights.keys())
	signal_artist_ids = list(favorite_artist_weights.keys())
	signal_similar_user_ids = list(similar_user_ids)
	social_album_ids = list(friend_album_weights.keys())

	signal_q = Q()
	if signal_genre_ids:
		signal_q |= Q(genres__id__in=signal_genre_ids)
	if signal_artist_ids:
		signal_q |= Q(artist_id__in=signal_artist_ids)
	if signal_similar_user_ids:
		signal_q |= Q(ratings__user_id__in=signal_similar_user_ids)
	if social_album_ids:
		signal_q |= Q(id__in=social_album_ids)

	if not signal_q.children:
		return []

	albums = (
		Album.objects.select_related('artist')
		.prefetch_related('genres')
		.filter(is_approved=True, artist__is_approved=True)
		.exclude(id__in=excluded_album_ids)
		.filter(signal_q)
		.distinct()
		.annotate(
			average_rating=Avg('ratings__rating'),
			ratings_count=Count('ratings', distinct=True),
		)
	)

	def popularity_score(avg: float | None, count: int) -> float:
		if not avg or count <= 0:
			return 0.0
		base = max(0.0, min(float(avg) / 5.0, 1.0))
		volume = min(float(count) / 10.0, 1.0)
		return base * volume

	def direct_social_score(album_id: int) -> float:
		if max_friend_weight <= 0:
			return 0.0
		return max(0.0, min(float(friend_album_weights.get(album_id, 0.0)) / max_friend_weight, 1.0))

	def similar_users_album_score(album_id: int) -> float:
		"""Return score in [0,1] based on ratings from similar users."""
		if not similar_user_ids:
			return 0.0

		ratings = similar_ratings_by_album.get(album_id)
		if not ratings:
			return 0.0

		w_sum = 0.0
		wr_sum = 0.0
		for user_id, rating in ratings:
			w = float(similar_user_weight_by_id.get(user_id, 0.0) or 0.0)
			if w <= 0:
				continue
			w_sum += w
			wr_sum += w * (float(rating) / 5.0)
		if w_sum <= 0:
			return 0.0
		return max(0.0, min(wr_sum / w_sum, 1.0))

	# Preload ratings for candidate albums from similar users
	similar_ratings_by_album: dict[int, list[tuple[int, int]]] = {}
	if similar_user_ids:
		rows = (
			AlbumRating.objects.filter(user_id__in=similar_user_ids)
			.values_list('album_id', 'user_id', 'rating')
		)
		for album_id, user_id, rating in rows:
			similar_ratings_by_album.setdefault(int(album_id), []).append((int(user_id), int(rating)))

	# Weights
	W_GENRE = 0.30
	W_ARTIST = 0.22
	W_SIMILAR = 0.20
	W_SOCIAL = 0.18
	W_POP = 0.10

	results = []
	for album in albums:
		if max_genre_weight <= 0:
			genre_score = 0.0
			best_genre_name = None
		else:
			best = 0
			best_genre_name = None
			for g in album.genres.all():
				w = favorite_genre_weights.get(int(g.id), 0.0)
				if w > best:
					best = w
					best_genre_name = g.name
			genre_score = best / max_genre_weight if best > 0 else 0.0

		artist_score = 1.0 if album.artist_id in followed_artist_ids else 0.0
		favorite_artist_score = (
			(float(favorite_artist_weights.get(int(album.artist_id), 0.0)) / float(max_artist_weight))
			if max_artist_weight > 0
			else 0.0
		)
		pop_score = popularity_score(
			getattr(album, 'average_rating', None),
			int(getattr(album, 'ratings_count', 0) or 0),
		)
		sim_score = similar_users_album_score(album.id)
		social_score = max(direct_social_score(album.id), sim_score)

		reason = ""
		if artist_score > 0:
			reason = f"Pentru că urmărești {album.artist.name}"
		elif favorite_artist_score > 0:
			reason = f"Pentru că ai interacționat des cu albumele lui {album.artist.name}"
		elif genre_score > 0 and best_genre_name:
			reason = f"Pentru că ai activitate frecventă în {best_genre_name}"
		elif social_score >= 0.15 and max_friend_weight > 0:
			reason = "Popular printre prietenii tăi"
		elif sim_score >= 0.15:
			reason = "Popular printre utilizatori cu gusturi similare"
		elif pop_score >= 0.25:
			reason = "Popular printre utilizatori"
		else:
			reason = "Recomandat pentru tine"

		score = (
			W_GENRE * float(genre_score)
			+ W_ARTIST * float(artist_score)
			+ W_SIMILAR * float(sim_score)
			+ W_SOCIAL * float(social_score)
			+ W_POP * float(pop_score)
		)
		if score <= 0:
			continue
		results.append({
			"album": album.title,
			"artist": album.artist.name,
			"album_id": album.id,
			"album_slug": album.slug,
			"cover_url": album.cover_url or "",
			"reason": reason,
			"genre_score": round(float(genre_score), 2),
			"similar_users_score": round(float(sim_score), 2),
			"popularity_score": round(float(pop_score), 2),
			"artist_slug": album.artist.slug,
			"score": round(float(score), 2),
			"_ratings_count": int(getattr(album, 'ratings_count', 0) or 0),
		})

	results.sort(key=lambda r: (-r["score"], -r["_ratings_count"], r["album"]))
	results = results[:limit]
	for r in results:
		r.pop('_ratings_count', None)
	return results


def _friend_ids_for_user(user) -> list[int]:
	"""Return a de-duplicated list of accepted friend user IDs for `user`."""
	friend_pairs = FriendRequest.objects.filter(
		Q(sender=user) | Q(receiver=user),
		status=FriendRequest.Status.ACCEPTED,
	).values_list('sender_id', 'receiver_id')

	friend_ids: set[int] = set()
	for sender_id, receiver_id in friend_pairs:
		if int(sender_id) != user.id:
			friend_ids.add(int(sender_id))
		if int(receiver_id) != user.id:
			friend_ids.add(int(receiver_id))
	return list(friend_ids)


def _friends_recommendations_payload(*, user, limit: int):
	"""Recommend albums based on friends' ratings/reviews (social proof)."""
	friend_ids = _friend_ids_for_user(user)
	if not friend_ids:
		return []

	excluded_album_ids = set(
		AlbumRating.objects.filter(user=user).values_list('album_id', flat=True)
	)

	# Keep DB work bounded: only positive friend ratings matter for recommendations.
	candidate_cap = max(200, min(500, int(limit) * 25))

	rating_rows = list(
		AlbumRating.objects.filter(
			user_id__in=friend_ids,
			rating__gte=4,
			album__is_approved=True,
			album__artist__is_approved=True,
		)
		.exclude(album_id__in=excluded_album_ids)
		.values('album_id')
		.annotate(
			friends_ratings_count=Count('id'),
			friends_distinct_raters=Count('user_id', distinct=True),
			friends_avg_rating=Avg('rating'),
			friends_five_count=Count('id', filter=Q(rating=5)),
			friends_four_plus_count=Count('id'),
		)
		.order_by('-friends_five_count', '-friends_four_plus_count', '-friends_distinct_raters', 'album_id')[:candidate_cap]
	)

	review_rows = list(
		AlbumReview.objects.filter(
			user_id__in=friend_ids,
			album__is_approved=True,
			album__artist__is_approved=True,
		)
		.exclude(album_id__in=excluded_album_ids)
		.values('album_id')
		.annotate(
			friends_reviews_count=Count('id'),
			friends_distinct_reviewers=Count('user_id', distinct=True),
		)
		.order_by('-friends_reviews_count', '-friends_distinct_reviewers', 'album_id')[:candidate_cap]
	)

	stats_by_album: dict[int, dict] = {}
	for row in rating_rows:
		album_id = int(row['album_id'])
		stats_by_album.setdefault(album_id, {}).update({
			"friends_ratings_count": int(row.get('friends_ratings_count', 0) or 0),
			"friends_distinct_raters": int(row.get('friends_distinct_raters', 0) or 0),
			"friends_avg_rating": float(row.get('friends_avg_rating') or 0.0),
			"friends_five_count": int(row.get('friends_five_count', 0) or 0),
			"friends_four_plus_count": int(row.get('friends_four_plus_count', 0) or 0),
		})
	for row in review_rows:
		album_id = int(row['album_id'])
		stats_by_album.setdefault(album_id, {}).update({
			"friends_reviews_count": int(row.get('friends_reviews_count', 0) or 0),
			"friends_distinct_reviewers": int(row.get('friends_distinct_reviewers', 0) or 0),
		})

	if not stats_by_album:
		return []

	scored: list[tuple[int, float]] = []
	for album_id, s in stats_by_album.items():
		five = int(s.get('friends_five_count', 0) or 0)
		four_plus = int(s.get('friends_four_plus_count', 0) or 0)
		four_only = max(0, int(four_plus) - int(five))
		distinct_raters = int(s.get('friends_distinct_raters', 0) or 0)
		distinct_reviewers = int(s.get('friends_distinct_reviewers', 0) or 0)
		avg = float(s.get('friends_avg_rating') or 0.0)
		reviews = int(s.get('friends_reviews_count', 0) or 0)

		# Only keep albums with a clear positive friend signal.
		if (five + four_only) <= 0 and reviews <= 0:
			continue

		# Social score: prioritize 5⭐ then ≥4⭐, then reviews.
		score = (
			3.0 * float(five)
			+ 2.0 * float(four_only)
			+ 1.5 * float(distinct_reviewers)
			+ 0.3 * float(distinct_raters)
			+ 0.1 * (float(avg) / 5.0)
		)
		if score <= 0:
			continue
		scored.append((int(album_id), float(score)))

	if not scored:
		return []

	# Stabilize ordering.
	scored.sort(key=lambda x: (-x[1], x[0]))
	ordered_album_ids = [album_id for album_id, _ in scored[: max(50, limit)]]

	albums = (
		Album.objects.select_related('artist')
		.filter(id__in=ordered_album_ids, is_approved=True, artist__is_approved=True)
	)
	album_by_id = {int(a.id): a for a in albums}

	# Build lightweight reasons (up to 2 friend names) for the selected set.
	five_names_by_album: dict[int, list[str]] = {}
	for album_id, username in (
		AlbumRating.objects.filter(
			album_id__in=ordered_album_ids,
			user_id__in=friend_ids,
			rating=5,
		)
		.select_related('user')
		.order_by('-created_at')
		.values_list('album_id', 'user__username')
	):
		lst = five_names_by_album.setdefault(int(album_id), [])
		if username and username not in lst and len(lst) < 2:
			lst.append(str(username))

	review_names_by_album: dict[int, list[str]] = {}
	for album_id, username in (
		AlbumReview.objects.filter(
			album_id__in=ordered_album_ids,
			user_id__in=friend_ids,
		)
		.select_related('user')
		.order_by('-created_at')
		.values_list('album_id', 'user__username')
	):
		lst = review_names_by_album.setdefault(int(album_id), [])
		if username and username not in lst and len(lst) < 2:
			lst.append(str(username))

	def _join_two(names: list[str]) -> str:
		if not names:
			return ""
		if len(names) == 1:
			return names[0]
		return f"{names[0]} și {names[1]}"

	results = []
	for album_id, score in scored:
		album = album_by_id.get(int(album_id))
		if not album:
			continue
		if len(results) >= limit:
			break

		s = stats_by_album.get(int(album_id), {})
		distinct_raters = int(s.get('friends_distinct_raters', 0) or 0)
		reviews = int(s.get('friends_reviews_count', 0) or 0)
		four_plus = int(s.get('friends_four_plus_count', 0) or 0)

		five_names = five_names_by_album.get(int(album_id), [])
		review_names = review_names_by_album.get(int(album_id), [])

		reason = ""
		if five_names:
			n = _join_two(five_names)
			if len(five_names) >= 2:
				reason = f"{n} au dat 5⭐ acestui album"
			else:
				reason = f"{n} a dat 5⭐ acestui album"
		elif four_plus >= 2:
			reason = f"{four_plus} prieteni au dat ≥4⭐ acestui album"
		elif review_names:
			n = _join_two(review_names)
			if reviews >= 2:
				reason = f"{n} au scris review-uri la acest album"
			else:
				reason = f"{n} a scris un review la acest album"
		elif distinct_raters > 0:
			reason = f"{distinct_raters} prieteni au evaluat acest album"
		else:
			reason = "Popular în cercul tău social"

		results.append({
			"album": album.title,
			"artist": album.artist.name,
			"album_id": album.id,
			"album_slug": album.slug,
			"cover_url": album.cover_url or "",
			"reason": reason,
			"artist_slug": album.artist.slug,
			"score": round(float(score), 2),
		})

	return results


class PlatformStatsView(APIView):
	permission_classes = [AllowAny]

	def get(self, request):
		limit_raw = str(request.query_params.get('limit', '')).strip()
		try:
			limit = int(limit_raw) if limit_raw else 10
		except ValueError:
			limit = 10
		limit = max(1, min(limit, 50))

		# Popular genres based on number of album ratings (counted per-genre).
		genre_qs = (
			Genre.objects.filter(
				albums__is_approved=True,
				albums__artist__is_approved=True,
			)
			.annotate(ratings_count=Count('albums__ratings'))
			.filter(ratings_count__gt=0)
			.order_by('-ratings_count', 'name')
		)

		total_genre_mentions = (
			AlbumRating.objects.filter(
				album__is_approved=True,
				album__artist__is_approved=True,
				album__genres__isnull=False,
			).count()
		)

		top_genres = []
		for g in genre_qs[:limit]:
			count = int(getattr(g, 'ratings_count', 0) or 0)
			pct = int(round((count / total_genre_mentions) * 100)) if total_genre_mentions > 0 else 0
			top_genres.append({
				"name": g.name,
				"percent": pct,
				"ratings": count,
			})

		# Artists with most ratings (based on ratings of their approved albums).
		artist_qs = (
			Artist.objects.filter(
				is_approved=True,
				albums__is_approved=True,
			)
			.annotate(ratings_count=Count('albums__ratings'))
			.filter(ratings_count__gt=0)
			.order_by('-ratings_count', 'name')
		)
		top_artists = [
			{
				"name": a.name,
				"ratings": int(getattr(a, 'ratings_count', 0) or 0),
			}
			for a in artist_qs[:limit]
		]

		# Albums with most reviews.
		album_qs = (
			Album.objects.filter(
				is_approved=True,
				artist__is_approved=True,
			)
			.annotate(reviews_count=Count('reviews'))
			.filter(reviews_count__gt=0)
			.order_by('-reviews_count', 'title')
		)
		top_albums = [
			{
				"title": a.title,
				"reviews": int(getattr(a, 'reviews_count', 0) or 0),
			}
			for a in album_qs[:limit]
		]

		return Response({
			"top_genres": top_genres,
			"top_artists": top_artists,
			"top_albums": top_albums,
		})


class ArtistSuggestView(generics.CreateAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = ArtistSuggestSerializer


class AlbumSuggestView(generics.CreateAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = AlbumSuggestSerializer


class SongSuggestView(generics.CreateAPIView):
	permission_classes = [IsAuthenticated]
	serializer_class = SongSuggestSerializer


class AlbumFilterOptionsView(APIView):
	"""Return filter dropdown options for the Albums page.

	Computed from the full approved catalog (not the current page), so UI
	can show all decades/years/months available.
	"""

	permission_classes = [AllowAny]

	def get(self, request):
		base_qs = Album.objects.filter(is_approved=True, artist__is_approved=True)

		# Years / months (distinct) from release_date.
		years_qs = base_qs.values_list('release_date__year', flat=True).distinct()
		years: list[int] = sorted(
			[int(y) for y in years_qs if y is not None],
			reverse=True,
		)

		months_qs = base_qs.values_list('release_date__month', flat=True).distinct()
		months: list[int] = sorted(
			[int(m) for m in months_qs if m is not None],
		)

		decades_set = {int(y // 10) * 10 for y in years if int(y) > 0}
		decades: list[int] = sorted(list(decades_set), reverse=True)

		# Genres used by approved albums.
		genres_qs = (
			Genre.objects.filter(albums__is_approved=True, albums__artist__is_approved=True)
			.distinct()
			.values('id', 'slug', 'name')
		)
		genres = sorted(
			[
				{
					"id": int(g.get('id') or 0),
					"slug": str(g.get('slug') or ''),
					"name": str(g.get('name') or g.get('slug') or ''),
				}
				for g in genres_qs
				if g.get('slug')
			],
			key=lambda x: x['name'].lower(),
		)

		return Response({
			"genres": genres,
			"years": years,
			"months": months,
			"decades": decades,
		})


class AlbumListView(generics.ListAPIView):
	queryset = (
		Album.objects.select_related('artist')
		.prefetch_related('genres')
		.filter(is_approved=True, artist__is_approved=True)
	)
	serializer_class = AlbumListSerializer
	pagination_class = AlbumPagination

	def get_queryset(self):
		qs = super().get_queryset()

		q = str(self.request.query_params.get('q', '')).strip()
		genre = str(self.request.query_params.get('genre', '')).strip()
		year_raw = str(self.request.query_params.get('year', '')).strip()
		month_raw = str(self.request.query_params.get('month', '')).strip()
		decade_raw = str(self.request.query_params.get('decade', '')).strip()
		sort_raw = str(self.request.query_params.get('sort', '')).strip().lower()
		pick_mode = str(self.request.query_params.get('pickMode', '')).strip().lower()

		if q:
			qs = qs.filter(Q(title__icontains=q) | Q(artist__name__icontains=q))

		if genre:
			qs = qs.filter(Q(genres__slug__iexact=genre) | Q(genres__name__iexact=genre)).distinct()

		if year_raw:
			try:
				year = int(year_raw)
			except ValueError:
				return qs.none()
			qs = qs.filter(release_date__year=year)

		if month_raw:
			try:
				month = int(month_raw)
			except ValueError:
				return qs.none()
			if month < 1 or month > 12:
				return qs.none()
			qs = qs.filter(release_date__month=month)

		if decade_raw:
			try:
				decade = int(decade_raw)
			except ValueError:
				return qs.none()
			start_year = (decade // 10) * 10
			end_year = start_year + 9
			qs = qs.filter(release_date__year__gte=start_year, release_date__year__lte=end_year)

		# Filter albums based on pick mode (for favorite album/song selection)
		if pick_mode == 'album':
			# Album picker: only show albums with >1 song (exclude singles)
			qs = qs.annotate(songs_count=Count('songs')).filter(songs_count__gt=1)

		sort_by = sort_raw if sort_raw in {'release_date', 'rating', 'ratings_count', 'my_rating'} else 'release_date'

		if sort_by in {'rating', 'ratings_count'}:
			avg_sq = (
				AlbumRating.objects.filter(album_id=OuterRef('pk'))
				.values('album_id')
				.annotate(avg=Avg('rating'))
				.values('avg')
			)
			cnt_sq = (
				AlbumRating.objects.filter(album_id=OuterRef('pk'))
				.values('album_id')
				.annotate(cnt=Count('id'))
				.values('cnt')
			)
			qs = qs.annotate(
				average_rating=Subquery(avg_sq, output_field=FloatField()),
				ratings_count=Coalesce(Subquery(cnt_sq, output_field=IntegerField()), Value(0)),
			)
			qs = qs.annotate(sort_rating=Coalesce('average_rating', Value(-1.0)))
			if sort_by == 'rating':
				# Highest rated first; tie-break on volume and recency.
				return qs.order_by('-sort_rating', '-ratings_count', '-release_date', 'id')
			# ratings_count
			return qs.order_by('-ratings_count', '-sort_rating', '-release_date', 'id')

		if sort_by == 'my_rating' and self.request.user.is_authenticated:
			my_sq = (
				AlbumRating.objects.filter(album_id=OuterRef('pk'), user=self.request.user)
				.values('rating')[:1]
			)
			qs = qs.annotate(my_rating=Subquery(my_sq, output_field=IntegerField()))
			qs = qs.annotate(sort_my_rating=Coalesce('my_rating', Value(-1)))
			return qs.order_by('-sort_my_rating', '-release_date', 'id')

		# Default: newest first.
		return qs.order_by('-release_date', 'id')


class AlbumDetailView(generics.RetrieveAPIView):
	serializer_class = AlbumDetailSerializer
	lookup_field = 'slug'

	def get_queryset(self):
		songs_qs = (
			Song.objects.select_related('artist', 'album')
			.prefetch_related(
				'genres',
				Prefetch('features', queryset=SongFeature.objects.select_related('artist')),
			)
			.filter(
				is_approved=True,
				artist__is_approved=True,
			)
			.annotate(
				average_rating=Avg('ratings__rating'),
				ratings_count=Count('ratings'),
			)
		)
		if self.request.user.is_authenticated:
			my_song_sq = (
				SongRating.objects.filter(song_id=OuterRef('pk'), user=self.request.user)
				.values('rating')[:1]
			)
			songs_qs = songs_qs.annotate(my_rating=Subquery(my_song_sq, output_field=IntegerField()))

		return (
			Album.objects.select_related('artist')
			.prefetch_related('genres', Prefetch('songs', queryset=songs_qs))
			.filter(is_approved=True, artist__is_approved=True)
			.annotate(
				average_rating=Avg('ratings__rating'),
				ratings_count=Count('ratings'),
				in_lists_count=Count('in_lists', distinct=True),
			)
		)

	def retrieve(self, request, *args, **kwargs):
		album = self.get_object()
		data = self.get_serializer(album).data

		# Total comments across all reviews for this album.
		data['comments_count'] = int(
			ReviewComment.objects.filter(review__album=album).count()
		)

		# Lists containing this album.
		data['in_lists_count'] = int(getattr(album, 'in_lists_count', 0) or 0)
		if request.user.is_authenticated:
			my_lists = (
				List.objects.filter(user=request.user, albums=album)
				.order_by('-updated_at', '-created_at')
				.values('id', 'name')
			)
			data['my_lists'] = [{'id': int(row['id']), 'name': row['name']} for row in my_lists]
		else:
			data['my_lists'] = []

		# Other albums from same artist.
		other_albums_limit = _parse_limit(
			request.query_params.get('other_albums_limit'),
			default=10,
			max_value=50,
		)
		other_albums_qs = (
			Album.objects.filter(
				artist=album.artist,
				is_approved=True,
				artist__is_approved=True,
			)
			.exclude(pk=album.pk)
			.select_related('artist')
			.prefetch_related('genres')
			.annotate(
				average_rating=Avg('ratings__rating'),
				ratings_count=Count('ratings'),
			)
			.order_by('-release_date', 'title')[:other_albums_limit]
		)
		data['other_albums_by_artist'] = AlbumInArtistSerializer(other_albums_qs, many=True).data

		# Rank within release year (by average rating desc, then votes desc).
		try:
			year = int(album.release_date.year)
		except Exception:
			year = None

		if year is not None:
			year_ids = list(
				Album.objects.filter(
					is_approved=True,
					artist__is_approved=True,
					release_date__year=year,
				)
				.annotate(
					avg=Avg('ratings__rating'),
					cnt=Count('ratings'),
				)
				.annotate(avg0=Coalesce('avg', Value(0.0)))
				.order_by('-avg0', '-cnt', '-id')
				.values_list('id', flat=True)
			)
			total = len(year_ids)
			data['year_rank_total'] = total
			try:
				idx = year_ids.index(album.id)
				data['year_rank'] = idx + 1
			except ValueError:
				data['year_rank'] = None
		else:
			data['year_rank'] = None
			data['year_rank_total'] = 0

		return Response(data)


class AlbumRecommendationsView(APIView):
	permission_classes = [AllowAny]

	def get(self, request, slug: str):
		limit = _parse_limit(request.query_params.get('limit'), default=12, max_value=50)
		album = get_object_or_404(
			Album.objects.prefetch_related('genres').select_related('artist'),
			slug=slug,
			is_approved=True,
			artist__is_approved=True,
		)
		genre_ids = list(album.genres.values_list('id', flat=True))

		# Collaborators = featured artists on songs in this album.
		collaborator_ids = list(
			SongFeature.objects.filter(song__album=album)
			.values_list('artist_id', flat=True)
			.distinct()
		)

		# Rating similarity: prefer albums with similar average rating.
		base_avg_row = AlbumRating.objects.filter(album=album).aggregate(avg=Avg('rating'))
		base_avg = float(base_avg_row.get('avg') or 0.0)

		if not genre_ids and not collaborator_ids:
			return Response([], status=200)

		signal_q = Q()
		if genre_ids:
			signal_q |= Q(genres__id__in=genre_ids)
		if collaborator_ids:
			signal_q |= Q(songs__features__artist_id__in=collaborator_ids)

		qs = (
			Album.objects.select_related('artist')
			.prefetch_related('genres')
			.filter(is_approved=True, artist__is_approved=True)
			.filter(signal_q)
			.exclude(pk=album.pk)
			.annotate(
				average_rating=Avg('ratings__rating'),
				ratings_count=Count('ratings', distinct=True),
				common_genres=Count('genres', filter=Q(genres__id__in=genre_ids), distinct=True),
				common_collaborators=(
					Count(
						'songs__features',
						filter=Q(songs__features__artist_id__in=collaborator_ids),
						distinct=True,
					)
					if collaborator_ids
					else Value(0, output_field=IntegerField())
				),
			)
			.annotate(
				sort_rating=Coalesce('average_rating', Value(-1.0)),
				rating_diff=Abs(Coalesce('average_rating', Value(0.0)) - Value(base_avg)),
			)
			.order_by(
				'-common_collaborators',
				'-common_genres',
				'rating_diff',
				'-sort_rating',
				'-ratings_count',
				'-release_date',
				'-id',
			)
			.distinct()
		)[:limit]

		return Response(AlbumListSerializer(qs, many=True).data, status=200)


class AlbumPublicListsView(APIView):
	permission_classes = [AllowAny]

	def get(self, request, slug: str):
		limit = _parse_limit(request.query_params.get('limit'), default=10, max_value=50)
		album = get_object_or_404(
			Album.objects.select_related('artist'),
			slug=slug,
			is_approved=True,
			artist__is_approved=True,
		)

		qs = (
			List.objects.select_related('user')
			.filter(is_public=True, albums=album)
			.filter(Q(user__privacy__public_lists=True) | Q(user__privacy__isnull=True))
			.annotate(
				albums_count=Count('albums', distinct=True),
				likes_count=Count('likes', distinct=True),
			)
			.order_by('-likes_count', '-created_at', '-id')
		)
		lists = list(qs[:limit])

		liked_ids: set[int] = set()
		if request.user.is_authenticated and lists:
			liked_ids = set(
				ListLike.objects.filter(user=request.user, list_id__in=[l.id for l in lists])
				.values_list('list_id', flat=True)
			)

		payload = [
			{
				"id": int(l.id),
				"name": l.name,
				"user_username": l.user.username,
				"created_at": l.created_at,
				"updated_at": l.updated_at,
				"albums_count": int(getattr(l, 'albums_count', 0) or 0),
				"likes_count": int(getattr(l, 'likes_count', 0) or 0),
				"is_liked": bool(l.id in liked_ids) if request.user.is_authenticated else False,
			}
			for l in lists
		]
		return Response(PublicListSerializer(payload, many=True).data, status=200)


class AlbumCommentsView(APIView):
	permission_classes = [AllowAny]

	def get(self, request, slug: str):
		limit = _parse_limit(request.query_params.get('limit'), default=30, max_value=100)
		album = get_object_or_404(
			Album.objects.select_related('artist'),
			slug=slug,
			is_approved=True,
			artist__is_approved=True,
		)

		comments = (
			ReviewComment.objects.select_related('user', 'review')
			.filter(review__album=album)
			.order_by('-created_at', '-id')[:limit]
		)
		return Response(ReviewCommentSerializer(comments, many=True).data, status=200)


class ArtistDetailView(generics.RetrieveAPIView):
	serializer_class = ArtistDetailSerializer
	lookup_field = 'slug'

	def get_queryset(self):
		albums_sort_raw = str(self.request.query_params.get('albums_sort', '')).strip().lower()
		songs_sort_raw = str(self.request.query_params.get('songs_sort', '')).strip().lower()
		albums_sort = albums_sort_raw if albums_sort_raw in {'release_date', 'rating', 'ratings_count', 'my_rating'} else 'release_date'
		songs_sort = songs_sort_raw if songs_sort_raw in {'release_date', 'rating', 'ratings_count', 'my_rating'} else 'release_date'

		albums_qs = (
			Album.objects.filter(is_approved=True)
			.select_related('artist')
			.prefetch_related('genres')
			.annotate(
				average_rating=Avg('ratings__rating'),
				ratings_count=Count('ratings'),
			)
			.annotate(sort_rating=Coalesce('average_rating', Value(-1.0)))
		)

		if albums_sort == 'release_date':
			albums_qs = albums_qs.order_by('-release_date', 'title', 'id')
		elif albums_sort == 'rating':
			albums_qs = albums_qs.order_by('-sort_rating', '-ratings_count', '-release_date', 'id')
		elif albums_sort == 'ratings_count':
			albums_qs = albums_qs.order_by('-ratings_count', '-sort_rating', '-release_date', 'id')
		elif albums_sort == 'my_rating' and self.request.user.is_authenticated:
			my_album_sq = (
				AlbumRating.objects.filter(album_id=OuterRef('pk'), user=self.request.user)
				.values('rating')[:1]
			)
			albums_qs = albums_qs.annotate(my_rating=Subquery(my_album_sq, output_field=IntegerField()))
			albums_qs = albums_qs.annotate(sort_my_rating=Coalesce('my_rating', Value(-1)))
			albums_qs = albums_qs.order_by('-sort_my_rating', '-release_date', 'id')
		else:
			albums_qs = albums_qs.order_by('-release_date', 'title', 'id')

		songs_qs = (
			Song.objects.select_related('artist', 'album')
			.prefetch_related('genres')
			.filter(is_approved=True)
			.filter(Q(album__isnull=True) | Q(album__is_approved=True, album__artist__is_approved=True))
			.annotate(
				average_rating=Avg('ratings__rating'),
				ratings_count=Count('ratings'),
			)
			.annotate(sort_rating=Coalesce('average_rating', Value(-1.0)))
			.annotate(sort_release_date=Coalesce('album__release_date', Value(date(1, 1, 1))))
		)

		if songs_sort == 'release_date':
			songs_qs = songs_qs.order_by('-sort_release_date', 'title', 'id')
		elif songs_sort == 'rating':
			songs_qs = songs_qs.order_by('-sort_rating', '-ratings_count', 'title', 'id')
		elif songs_sort == 'ratings_count':
			songs_qs = songs_qs.order_by('-ratings_count', '-sort_rating', 'title', 'id')
		elif songs_sort == 'my_rating' and self.request.user.is_authenticated:
			my_song_sq = (
				SongRating.objects.filter(song_id=OuterRef('pk'), user=self.request.user)
				.values('rating')[:1]
			)
			songs_qs = songs_qs.annotate(my_rating=Subquery(my_song_sq, output_field=IntegerField()))
			songs_qs = songs_qs.annotate(sort_my_rating=Coalesce('my_rating', Value(-1)))
			songs_qs = songs_qs.order_by('-sort_my_rating', 'title', 'id')
		else:
			songs_qs = songs_qs.order_by('-sort_release_date', 'title', 'id')

		return (
			Artist.objects.filter(is_approved=True)
			.annotate(
				albums_count=Count(
					'albums',
					filter=Q(albums__is_approved=True),
					distinct=True,
				),
				songs_count=Count(
					'songs',
					filter=(
						Q(songs__is_approved=True)
						& (Q(songs__album__isnull=True) | Q(songs__album__is_approved=True))
					),
					distinct=True,
				),
				followers_count=Count('followers', distinct=True),
			)
			.prefetch_related(
				'genres',
				Prefetch('albums', queryset=albums_qs),
				Prefetch('songs', queryset=songs_qs),
			)
		)

	def retrieve(self, request, *args, **kwargs):
		artist = self.get_object()
		data = self.get_serializer(artist).data

		# User-specific counts
		if request.user.is_authenticated:
			data['my_albums_listened_count'] = int(
				AlbumListen.objects.filter(
					user=request.user,
					album__artist=artist,
					album__is_approved=True,
					album__artist__is_approved=True,
				)
				.values('album_id')
				.distinct()
				.count()
			)
			# There is no SongListen model; approximate "listened" as "rated".
			data['my_songs_listened_count'] = int(
				SongRating.objects.filter(
					user=request.user,
					song__artist=artist,
					song__is_approved=True,
					song__artist__is_approved=True,
				)
				.filter(Q(song__album__isnull=True) | Q(song__album__is_approved=True, song__album__artist__is_approved=True))
				.values('song_id')
				.distinct()
				.count()
			)
		else:
			data['my_albums_listened_count'] = 0
			data['my_songs_listened_count'] = 0

		top_reviews_limit = _parse_limit(
			request.query_params.get('top_reviews_limit'),
			default=5,
			max_value=20,
		)
		reviews_qs = (
			AlbumReview.objects.select_related('user', 'album', 'album__artist')
			.filter(
				album__artist=artist,
				album__is_approved=True,
				album__artist__is_approved=True,
			)
			.annotate(likes_count=Count('likes', distinct=True))
			.order_by('-likes_count', '-created_at')[:top_reviews_limit]
		)
		data['top_reviews'] = PopularAlbumReviewSerializer(reviews_qs, many=True).data

		if request.user.is_authenticated:
			lists_limit = _parse_limit(
				request.query_params.get('lists_limit'),
				default=20,
				max_value=50,
			)
			lists_qs = (
				List.objects.filter(user=request.user)
				.filter(
					albums__artist=artist,
					albums__is_approved=True,
					albums__artist__is_approved=True,
				)
				.annotate(
					albums_count=Count('albums', distinct=True),
					matching_albums_count=Count(
						'albums',
						filter=Q(
							albums__artist=artist,
							albums__is_approved=True,
							albums__artist__is_approved=True,
						),
						distinct=True,
					),
				)
				.order_by('-matching_albums_count', '-updated_at', '-created_at')
				.distinct()[:lists_limit]
			)
			data['my_lists_with_artist_albums'] = [
				{
					'id': int(l.id),
					'name': l.name,
					'albums_count': int(getattr(l, 'albums_count', 0) or 0),
					'matching_albums_count': int(getattr(l, 'matching_albums_count', 0) or 0),
					'updated_at': getattr(l, 'updated_at', None),
				}
				for l in lists_qs
			]
		else:
			data['my_lists_with_artist_albums'] = []

		return Response(data)


class ArtistDiscographyView(APIView):
	permission_classes = [AllowAny]

	def get(self, request, slug: str):
		artist = get_object_or_404(
			Artist.objects.filter(is_approved=True),
			slug=slug,
		)

		albums_qs = (
			Album.objects.select_related('artist')
			.prefetch_related('genres')
			.filter(
				artist=artist,
				is_approved=True,
				artist__is_approved=True,
			)
			.annotate(
				average_rating=Avg('ratings__rating'),
				ratings_count=Count('ratings'),
				approved_tracks_count=Count('songs', filter=Q(songs__is_approved=True), distinct=True),
			)
		)

		# Group by MusicBrainz primary type.
		groups: dict[str, list] = {
			"album": [],
			"single": [],
			"ep": [],
			"compilation": [],
			"other": [],
		}
		for a in albums_qs.order_by('-release_date', 'title', 'id'):
			t = str(getattr(a, 'mb_primary_type', '') or '').strip().lower()
			tracks = int(getattr(a, 'approved_tracks_count', 0) or 0)

			# Heuristic: if we don't have a proper MB type yet (or it says 'album'),
			# classify 1-track releases as singles.
			if tracks == 1 and (not t or t == 'album'):
				groups['single'].append(a)
				continue

			if t in groups:
				groups[t].append(a)
			elif t:
				groups['other'].append(a)
			else:
				groups['album'].append(a)

		appears_on_qs = (
			Song.objects.select_related('artist', 'album')
			.prefetch_related('genres')
			.filter(
				is_approved=True,
				artist__is_approved=True,
				features__artist=artist,
			)
			.exclude(artist=artist)
			.filter(Q(album__isnull=True) | Q(album__is_approved=True, album__artist__is_approved=True))
			.annotate(
				average_rating=Avg('ratings__rating'),
				ratings_count=Count('ratings'),
			)
			.order_by('-album__release_date', 'title', 'id')
		)

		payload = {
			"artist": {
				"id": int(artist.id),
				"name": artist.name,
				"slug": artist.slug,
			},
			"albums": AlbumInArtistSerializer(groups['album'], many=True).data,
			"singles": AlbumInArtistSerializer(groups['single'], many=True).data,
			"eps": AlbumInArtistSerializer(groups['ep'], many=True).data,
			"compilations": AlbumInArtistSerializer(groups['compilation'], many=True).data,
			"other": AlbumInArtistSerializer(groups['other'], many=True).data,
			"appears_on": SongSerializer(appears_on_qs, many=True).data,
		}
		return Response(payload, status=200)


class ArtistSimilarArtistsView(APIView):
	permission_classes = [AllowAny]

	def get(self, request, slug: str):
		limit = _parse_limit(request.query_params.get('limit'), default=12, max_value=50)
		artist = get_object_or_404(Artist.objects.filter(is_approved=True), slug=slug)

		edges = (
			ArtistSimilarity.objects.select_related('to_artist')
			.filter(from_artist=artist, to_artist__is_approved=True)
			.annotate(match_sort=Coalesce('match', Value(-1.0)))
			.order_by('-match_sort', '-created_at', '-id')[:limit]
		)

		items = []
		for e in edges:
			to_artist = getattr(e, 'to_artist', None)
			if not to_artist:
				continue
			# Attach match onto the artist instance for serialization.
			to_artist.match = getattr(e, 'match', None)
			items.append(to_artist)

		return Response(SimilarArtistSerializer(items, many=True).data, status=200)


class ArtistTopSongsView(APIView):
	permission_classes = [AllowAny]

	def get(self, request, slug: str):
		limit = _parse_limit(request.query_params.get('limit'), default=10, max_value=50)
		sort_raw = str(request.query_params.get('sort') or '').strip().lower()
		sort = sort_raw if sort_raw in {'rating', 'ratings_count'} else 'rating'

		artist = get_object_or_404(Artist.objects.filter(is_approved=True), slug=slug)
		qs = (
			Song.objects.select_related('artist', 'album')
			.prefetch_related(
				'genres',
				Prefetch('features', queryset=SongFeature.objects.select_related('artist')),
			)
			.filter(
				artist=artist,
				is_approved=True,
				artist__is_approved=True,
			)
			.filter(Q(album__isnull=True) | Q(album__is_approved=True, album__artist__is_approved=True))
			.annotate(
				average_rating=Avg('ratings__rating'),
				ratings_count=Count('ratings'),
			)
			.annotate(sort_rating=Coalesce('average_rating', Value(-1.0)))
		)

		if sort == 'ratings_count':
			qs = qs.order_by('-ratings_count', '-sort_rating', 'title', 'id')
		else:
			qs = qs.order_by('-sort_rating', '-ratings_count', 'title', 'id')

		return Response(SongInArtistSerializer(qs[:limit], many=True).data, status=200)


class SongDetailView(generics.RetrieveAPIView):
	queryset = (
		Song.objects.select_related('artist', 'album')
		.prefetch_related(
			'genres',
			Prefetch('features', queryset=SongFeature.objects.select_related('artist')),
		)
		.filter(
			is_approved=True,
			artist__is_approved=True,
		)
		.filter(
			Q(album__isnull=True) | Q(album__is_approved=True, album__artist__is_approved=True),
		)
	)
	serializer_class = SongSerializer
	lookup_field = 'slug'


class SearchView(APIView):
	permission_classes = [AllowAny]

	def get(self, request):
		q = str(request.query_params.get('q', '')).strip()
		limit_raw = str(request.query_params.get('limit', '')).strip()
		genre_raw = str(request.query_params.get('genre', '')).strip()
		year_raw = str(request.query_params.get('year', '')).strip()
		country_raw = str(request.query_params.get('country', '')).strip().lower()
		min_rating_raw = str(request.query_params.get('min_rating', '')).strip()
		reviewed_only_raw = str(request.query_params.get('reviewed_only', '')).strip().lower()
		followed_only_raw = str(request.query_params.get('followed_only', '')).strip().lower()

		limit = 20
		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 20
		limit = max(1, min(limit, 50))

		reviewed_only = reviewed_only_raw in {'1', 'true', 'yes', 'on'}
		followed_only = followed_only_raw in {'1', 'true', 'yes', 'on'}
		if not q:
			return Response({
				"artists": [],
				"albums": [],
				"songs": [],
			})

		album_filters_active = any([
			genre_raw,
			year_raw,
			country_raw,
			min_rating_raw,
			reviewed_only,
			followed_only,
		])

		artists_qs = Artist.objects.filter(is_approved=True, name__icontains=q)
		albums_qs = (
			Album.objects.select_related('artist')
			.filter(is_approved=True, artist__is_approved=True)
			.filter(Q(title__icontains=q) | Q(artist__name__icontains=q))
		)
		songs_qs = (
			Song.objects.select_related('artist', 'album')
			.filter(
				is_approved=True,
				artist__is_approved=True,
			)
			.filter(
				Q(title__icontains=q) | Q(artist__name__icontains=q) | Q(album__title__icontains=q)
			)
			.filter(Q(album__isnull=True) | Q(album__is_approved=True, album__artist__is_approved=True))
			.order_by('title')
		)

		# Optional: keep only followed artists/albums (requires auth).
		if followed_only:
			if request.user and request.user.is_authenticated:
				artists_qs = artists_qs.filter(followers__user=request.user)
				albums_qs = albums_qs.filter(artist__followers__user=request.user)
			else:
				artists_qs = artists_qs.none()
				albums_qs = albums_qs.none()

		# Album-only filters (optional).
		if genre_raw:
			albums_qs = albums_qs.filter(genres__name__icontains=genre_raw)
		if year_raw:
			try:
				year = int(year_raw)
			except ValueError:
				year = 0
			if year > 0:
				albums_qs = albums_qs.filter(release_date__year=year)
		if country_raw:
			if country_raw in {'ro', 'romania', 'românia'}:
				albums_qs = albums_qs.filter(artist__is_romanian=True)
			elif country_raw in {'intl', 'international', 'other', 'non-ro'}:
				albums_qs = albums_qs.filter(artist__is_romanian=False)
		if reviewed_only:
			albums_qs = albums_qs.filter(reviews__isnull=False)
		if min_rating_raw:
			try:
				min_rating = float(min_rating_raw)
			except ValueError:
				min_rating = 0.0
			if min_rating > 0:
				min_rating = max(1.0, min(min_rating, 5.0))
				albums_qs = (
					albums_qs.annotate(average_rating=Avg('ratings__rating'))
					.filter(average_rating__gte=min_rating)
				)

		if album_filters_active:
			artists_qs = artists_qs.filter(Exists(albums_qs.filter(artist_id=OuterRef('pk'))))
		artists_qs = artists_qs.distinct().order_by('name', 'id')
		albums_qs = albums_qs.distinct().order_by('title', 'id')
		if album_filters_active:
			songs_qs = songs_qs.filter(album__isnull=False).filter(Exists(albums_qs.filter(pk=OuterRef('album_id'))))


		return Response({
			"artists": SearchArtistSerializer(artists_qs[:limit], many=True).data,
			"albums": SearchAlbumSerializer(albums_qs[:limit], many=True).data,
			"songs": SearchSongSerializer(songs_qs[:limit], many=True).data,
		})


class TopAlbumsView(generics.ListAPIView):
	permission_classes = [AllowAny]
	serializer_class = TopAlbumSerializer

	def get_queryset(self):
		limit_raw = str(self.request.query_params.get('limit', '')).strip()
		year_raw = str(self.request.query_params.get('year', '')).strip()
		decade_raw = str(self.request.query_params.get('decade', '')).strip()

		qs = (
			Album.objects.select_related('artist')
			.filter(is_approved=True, artist__is_approved=True)
			.annotate(
				average_rating=Avg('ratings__rating'),
				ratings_count=Count('ratings'),
			)
			.annotate(
				sort_rating=Coalesce('average_rating', Value(-1.0)),
			)
		)

		if year_raw:
			try:
				year = int(year_raw)
			except ValueError:
				return qs.none()
			qs = qs.filter(release_date__year=year)

		if decade_raw:
			try:
				decade = int(decade_raw)
			except ValueError:
				return qs.none()
			start_year = (decade // 10) * 10
			end_year = start_year + 9
			qs = qs.filter(release_date__year__gte=start_year, release_date__year__lte=end_year)

		qs = qs.order_by('-sort_rating', '-ratings_count', 'title')

		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 0
			if limit > 0:
				limit = min(limit, 50)
				qs = qs[:limit]

		return qs


class TopArtistsView(generics.ListAPIView):
	permission_classes = [AllowAny]
	serializer_class = TopArtistSerializer

	def get_queryset(self):
		limit_raw = str(self.request.query_params.get('limit', '')).strip()

		qs = (
			Artist.objects.filter(is_approved=True)
			.annotate(
				average_rating=Avg(
					'albums__ratings__rating',
					filter=Q(albums__is_approved=True),
				),
				ratings_count=Count(
					'albums__ratings',
					filter=Q(albums__is_approved=True),
					distinct=True,
				),
				albums_count=Count(
					'albums',
					filter=Q(albums__is_approved=True),
					distinct=True,
				),
			)
			.annotate(sort_rating=Coalesce('average_rating', Value(-1.0)))
			.filter(ratings_count__gt=0)
			.order_by('-sort_rating', '-ratings_count', 'name', 'id')
		)

		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 0
			if limit > 0:
				limit = min(limit, 200)
				qs = qs[:limit]

		return qs


class RandomArtistView(APIView):
	permission_classes = [AllowAny]

	def get(self, request):
		qs = Artist.objects.filter(is_approved=True).order_by('id')
		count = qs.count()
		if count <= 0:
			return Response({"detail": "No approved artists found."}, status=404)

		offset = random.randrange(count)
		artist = qs[offset]
		return Response(RandomArtistSerializer(artist).data, status=200)


class RandomAlbumView(APIView):
	permission_classes = [AllowAny]

	def get(self, request):
		qs = Album.objects.filter(is_approved=True, artist__is_approved=True).order_by('id')
		count = qs.count()
		if count <= 0:
			return Response({"detail": "No approved albums found."}, status=404)

		offset = random.randrange(count)
		album = qs[offset]
		return Response(AlbumListSerializer(album).data, status=200)


class NewReleasesView(generics.ListAPIView):
	permission_classes = [AllowAny]
	serializer_class = AlbumListSerializer

	def get_queryset(self):
		limit_raw = str(self.request.query_params.get('limit', '')).strip()

		qs = (
			Album.objects.select_related('artist')
			.prefetch_related('genres')
			.filter(is_approved=True, artist__is_approved=True)
			.order_by('-release_date', 'title')
		)

		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 0
			if limit > 0:
				limit = min(limit, 50)
				qs = qs[:limit]

		return qs


class ReleasedOnThisDayView(generics.ListAPIView):
	permission_classes = [AllowAny]
	serializer_class = AlbumListSerializer

	def get_queryset(self):
		limit_raw = str(self.request.query_params.get('limit', '')).strip()
		month_raw = str(self.request.query_params.get('month', '')).strip()
		day_raw = str(self.request.query_params.get('day', '')).strip()

		today = date.today()
		month = today.month
		day = today.day

		if month_raw:
			try:
				month = int(month_raw)
			except ValueError:
				return Album.objects.none()
		if day_raw:
			try:
				day = int(day_raw)
			except ValueError:
				return Album.objects.none()

		if month < 1 or month > 12 or day < 1 or day > 31:
			return Album.objects.none()

		qs = (
			Album.objects.select_related('artist')
			.prefetch_related('genres')
			.filter(
				is_approved=True,
				artist__is_approved=True,
				release_date__month=month,
				release_date__day=day,
			)
			.order_by('-release_date', 'title')
		)

		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 0
			if limit > 0:
				limit = min(limit, 50)
				qs = qs[:limit]

		return qs


class RecommendationsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		limit = _parse_limit(request.query_params.get('limit', ''), default=20, max_value=50)
		exclude_in_lists_raw = str(request.query_params.get('exclude_in_lists', '')).strip().lower()
		exclude_in_lists = exclude_in_lists_raw in ("1", "true", "yes", "y")
		excluded_album_ids = _user_signal_album_ids(request.user)
		if exclude_in_lists:
			excluded_album_ids.update(
				ListAlbum.objects.filter(list__user=request.user).values_list('album_id', flat=True)
			)

		cache_key = f'recommendations:user:item:{request.user.id}'
		item_recs = cache.get(cache_key)
		hybrid_results = _recommendations_payload(user=request.user, limit=limit, exclude_in_lists=exclude_in_lists)
		merged = _merge_recommendation_payloads(hybrid_results, item_recs or [], limit, excluded_album_ids=excluded_album_ids)
		return Response(RecommendationSerializer(merged, many=True).data)


class FriendsRecommendationsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		limit = _parse_limit(request.query_params.get('limit', ''), default=10, max_value=50)
		results = _friends_recommendations_payload(user=request.user, limit=limit)
		return Response(RecommendationSerializer(results, many=True).data)


class HomeView(APIView):
	permission_classes = [AllowAny]

	def get(self, request):
		# Limits per section (small by default to keep homepage fast)
		rec_limit = _parse_limit(request.query_params.get('rec_limit', ''), default=8, max_value=20)
		activity_limit = _parse_limit(request.query_params.get('activity_limit', ''), default=10, max_value=50)
		popular_limit = _parse_limit(request.query_params.get('popular_limit', ''), default=10, max_value=50)
		popular_reviews_limit = _parse_limit(request.query_params.get('popular_reviews_limit', ''), default=10, max_value=50)
		weekly_popular_limit = _parse_limit(request.query_params.get('weekly_popular_limit', ''), default=10, max_value=50)
		weekly_listens_limit = _parse_limit(request.query_params.get('weekly_listens_limit', ''), default=10, max_value=50)
		anticipated_limit = _parse_limit(request.query_params.get('anticipated_limit', ''), default=10, max_value=50)
		genres_limit = _parse_limit(request.query_params.get('genres_limit', ''), default=12, max_value=50)
		best_limit = _parse_limit(request.query_params.get('best_limit', ''), default=5, max_value=20)
		new_limit = _parse_limit(request.query_params.get('new_limit', ''), default=10, max_value=50)
		recent_limit = _parse_limit(request.query_params.get('recent_limit', ''), default=10, max_value=50)
		top_2025_limit = _parse_limit(request.query_params.get('top_2025_limit', ''), default=5, max_value=20)
		friends_rec_limit = _parse_limit(request.query_params.get('friends_rec_limit', ''), default=8, max_value=20)
		trending_limit = _parse_limit(request.query_params.get('trending_limit', ''), default=10, max_value=50)
		discussed_limit = _parse_limit(request.query_params.get('discussed_limit', ''), default=10, max_value=50)

		genres_qs = Genre.objects.order_by('name')[:genres_limit]

		# Public sections
		popular_qs = (
			Album.objects.select_related('artist')
			.filter(is_approved=True, artist__is_approved=True)
			.annotate(
				average_rating=Avg('ratings__rating'),
				ratings_count=Count('ratings'),
			)
			.order_by('-ratings_count', '-average_rating', 'title')[:popular_limit]
		)

		# Weekly engagement: NOT real "listens" (we don't track plays). This is based on
		# interactions in the last 7 days: ratings + reviews + review likes.
		weekly_since = timezone.now() - timedelta(days=7)
		cur_since = weekly_since
		prev_since = timezone.now() - timedelta(days=14)

		weekly_most_listened_qs = (
			Album.objects.select_related('artist')
			.filter(is_approved=True, artist__is_approved=True)
			.annotate(
				average_rating=Avg('ratings__rating'),
				ratings_count=Count('ratings', distinct=True),
				listens_count=Count(
					'listens',
					filter=Q(listens__listened_at__gte=weekly_since),
					distinct=True,
				),
			)
			.filter(listens_count__gt=0)
			.order_by('-listens_count', '-ratings_count', 'title')[:weekly_listens_limit]
		)

		# Popular reviews of the week: order by likes in last 7 days.
		popular_reviews_qs = (
			AlbumReview.objects.select_related('user', 'album', 'album__artist')
			.filter(album__is_approved=True, album__artist__is_approved=True)
			.annotate(
				likes_count=Count('likes', filter=Q(likes__created_at__gte=weekly_since), distinct=True),
			)
			.order_by('-likes_count', '-created_at')[:popular_reviews_limit]
		)
		weekly_popular_qs = (
			Album.objects.select_related('artist')
			.filter(is_approved=True, artist__is_approved=True)
			.annotate(
				average_rating=Avg('ratings__rating'),
				ratings_count=Count('ratings', distinct=True),
				weekly_ratings=Count(
					'ratings',
					filter=Q(ratings__created_at__gte=weekly_since),
					distinct=True,
				),
				weekly_reviews=Count(
					'reviews',
					filter=Q(reviews__created_at__gte=weekly_since),
					distinct=True,
				),
				weekly_review_likes=Count(
					'reviews__likes',
					filter=Q(reviews__likes__created_at__gte=weekly_since),
					distinct=True,
				),
			)
			.annotate(
				engagement_score=F('weekly_ratings') + F('weekly_reviews') + F('weekly_review_likes'),
			)
			.order_by('-engagement_score', '-weekly_reviews', '-weekly_ratings', 'title')[:weekly_popular_limit]
		)

		best_qs = (
			Album.objects.select_related('artist')
			.filter(is_approved=True, artist__is_approved=True)
			.annotate(
				average_rating=Avg('ratings__rating'),
				ratings_count=Count('ratings'),
			)
			.annotate(
				sort_rating=Coalesce('average_rating', Value(-1.0)),
			)
			.filter(ratings_count__gt=0)
			.order_by('-sort_rating', '-ratings_count', 'title')[:best_limit]
		)

		new_qs = (
			Album.objects.select_related('artist')
			.prefetch_related('genres')
			.filter(is_approved=True, artist__is_approved=True)
			.order_by('-release_date', 'title')[:new_limit]
		)

		today = date.today()

		anticipated_qs = (
			Album.objects.select_related('artist')
			.filter(is_approved=True, artist__is_approved=True, release_date__gt=today)
			.annotate(
				ratings_count=Count('ratings', distinct=True),
				reviews_count=Count('reviews', distinct=True),
			)
			.annotate(interest_score=F('reviews_count'))
			.order_by('-reviews_count', 'release_date', 'title')[:anticipated_limit]
		)

		# Albums released in the last 7 days (inclusive of today, same semantics as RecentAlbumsView)
		start = today - timedelta(days=7)
		recent_qs = (
			Album.objects.select_related('artist')
			.prefetch_related('genres')
			.filter(
				is_approved=True,
				artist__is_approved=True,
				release_date__gt=start,
				release_date__lte=today,
			)
			.order_by('-release_date', 'title')[:recent_limit]
		)

		# Top-rated albums released in 2025
		top_2025_qs = (
			Album.objects.select_related('artist')
			.filter(
				is_approved=True,
				artist__is_approved=True,
				release_date__year=2025,
			)
			.annotate(
				average_rating=Avg('ratings__rating'),
				ratings_count=Count('ratings'),
			)
			.annotate(
				sort_rating=Coalesce('average_rating', Value(-1.0)),
			)
			.order_by('-sort_rating', '-ratings_count', 'title')[:top_2025_limit]
		)

		recommendations = []
		friends_recommendations = []
		friends_activity = []
		if request.user and request.user.is_authenticated:
			hybrid_recommendations = _recommendations_payload(
				user=request.user,
				limit=rec_limit,
				exclude_in_lists=False,
			)
			cache_key = f'recommendations:user:item:{request.user.id}'
			item_recs = cache.get(cache_key) or []
			excluded_album_ids = _user_signal_album_ids(request.user)
			recommendations = _merge_recommendation_payloads(
				hybrid_recommendations,
				item_recs,
				rec_limit,
				excluded_album_ids=excluded_album_ids,
			)

			friend_ids = set(_friend_ids_for_user(request.user))
			friends_recommendations = _friends_recommendations_payload(
				user=request.user,
				limit=friends_rec_limit,
			)

			if friend_ids:
				act_qs = (
					UserActivity.objects.select_related('actor')
					.filter(actor_id__in=list(friend_ids))
					.order_by('-created_at')[:activity_limit]
				)
				friends_activity = UserActivitySerializer(act_qs, many=True).data

		# Trending: "în creștere" = delta(last 7d score vs previous 7d)
		# Album score is based on: listens + 2*reviews + comments
		trending_albums = []
		if trending_limit > 0:
			album_rows = (
				Album.objects.select_related('artist')
				.filter(is_approved=True, artist__is_approved=True)
				.annotate(
					cur_listens=Count('listens', filter=Q(listens__listened_at__gte=cur_since), distinct=True),
					prev_listens=Count(
						'listens',
						filter=Q(listens__listened_at__gte=prev_since, listens__listened_at__lt=cur_since),
						distinct=True,
					),
					cur_reviews=Count('reviews', filter=Q(reviews__created_at__gte=cur_since), distinct=True),
					prev_reviews=Count(
						'reviews',
						filter=Q(reviews__created_at__gte=prev_since, reviews__created_at__lt=cur_since),
						distinct=True,
					),
					cur_comments=Count('reviews__comments', filter=Q(reviews__comments__created_at__gte=cur_since), distinct=True),
					prev_comments=Count(
						'reviews__comments',
						filter=Q(reviews__comments__created_at__gte=prev_since, reviews__comments__created_at__lt=cur_since),
						distinct=True,
					),
				)
				.annotate(
					current_score=ExpressionWrapper(
						F('cur_listens') + 2 * F('cur_reviews') + F('cur_comments'),
						output_field=IntegerField(),
					),
					previous_score=ExpressionWrapper(
						F('prev_listens') + 2 * F('prev_reviews') + F('prev_comments'),
						output_field=IntegerField(),
					),
				)
				.annotate(delta=ExpressionWrapper(F('current_score') - F('previous_score'), output_field=IntegerField()))
				.filter(delta__gt=0)
				.order_by('-delta', '-current_score', '-cur_listens', '-cur_reviews', '-id')
				.values(
					'id',
					'title',
					'slug',
					'cover_url',
					'release_date',
					'artist__name',
					'artist__slug',
					'current_score',
					'previous_score',
					'delta',
				)[:trending_limit]
			)
			trending_albums = [
				{
					'id': int(r['id']),
					'title': r['title'],
					'slug': r['slug'],
					'cover_url': r.get('cover_url') or '',
					'release_date': r.get('release_date'),
					'artist_name': r.get('artist__name') or '',
					'artist_slug': r.get('artist__slug') or '',
					'current_score': int(r.get('current_score') or 0),
					'previous_score': int(r.get('previous_score') or 0),
					'delta': int(r.get('delta') or 0),
				}
				for r in list(album_rows)
			]

		trending_artists = []
		if trending_limit > 0:
			artist_rows = (
				Artist.objects.filter(is_approved=True)
				.annotate(
					cur_follows=Count('followers', filter=Q(followers__created_at__gte=cur_since), distinct=True),
					prev_follows=Count(
						'followers',
						filter=Q(followers__created_at__gte=prev_since, followers__created_at__lt=cur_since),
						distinct=True,
					),
					cur_listens=Count('albums__listens', filter=Q(albums__listens__listened_at__gte=cur_since), distinct=True),
					prev_listens=Count(
						'albums__listens',
						filter=Q(albums__listens__listened_at__gte=prev_since, albums__listens__listened_at__lt=cur_since),
						distinct=True,
					),
					cur_reviews=Count('albums__reviews', filter=Q(albums__reviews__created_at__gte=cur_since), distinct=True),
					prev_reviews=Count(
						'albums__reviews',
						filter=Q(albums__reviews__created_at__gte=prev_since, albums__reviews__created_at__lt=cur_since),
						distinct=True,
					),
				)
				.annotate(
					current_score=ExpressionWrapper(
						(2 * F('cur_follows')) + F('cur_listens') + (2 * F('cur_reviews')),
						output_field=IntegerField(),
					),
					previous_score=ExpressionWrapper(
						(2 * F('prev_follows')) + F('prev_listens') + (2 * F('prev_reviews')),
						output_field=IntegerField(),
					),
				)
				.annotate(delta=ExpressionWrapper(F('current_score') - F('previous_score'), output_field=IntegerField()))
				.filter(delta__gt=0)
				.order_by('-delta', '-current_score', '-cur_follows', '-cur_listens', '-id')
				.values('id', 'name', 'slug', 'image_url', 'current_score', 'previous_score', 'delta')[:trending_limit]
			)
			trending_artists = [
				{
					'id': int(r['id']),
					'name': r['name'],
					'slug': r['slug'],
					'image_url': r.get('image_url') or '',
					'current_score': int(r.get('current_score') or 0),
					'previous_score': int(r.get('previous_score') or 0),
					'delta': int(r.get('delta') or 0),
				}
				for r in list(artist_rows)
			]

		# Most discussed (last 7 days): reviews + comments
		most_discussed_albums = []
		if discussed_limit > 0:
			disc_rows = (
				Album.objects.select_related('artist')
				.filter(is_approved=True, artist__is_approved=True)
				.annotate(
					weekly_reviews=Count('reviews', filter=Q(reviews__created_at__gte=weekly_since), distinct=True),
					weekly_comments=Count('reviews__comments', filter=Q(reviews__comments__created_at__gte=weekly_since), distinct=True),
				)
				.annotate(
					discussions_count=ExpressionWrapper(
						F('weekly_reviews') + F('weekly_comments'),
						output_field=IntegerField(),
					),
				)
				.filter(discussions_count__gt=0)
				.order_by('-discussions_count', '-weekly_comments', '-weekly_reviews', '-id')
				.values(
					'id',
					'title',
					'slug',
					'cover_url',
					'release_date',
					'artist__name',
					'artist__slug',
					'discussions_count',
				)[:discussed_limit]
			)
			most_discussed_albums = [
				{
					'id': int(r['id']),
					'title': r['title'],
					'slug': r['slug'],
					'cover_url': r.get('cover_url') or '',
					'release_date': r.get('release_date'),
					'artist_name': r.get('artist__name') or '',
					'artist_slug': r.get('artist__slug') or '',
					'discussions_count': int(r.get('discussions_count') or 0),
				}
				for r in list(disc_rows)
			]

		payload = {
			"genres": GenreSerializer(genres_qs, many=True).data,
			"recommendations": RecommendationSerializer(recommendations, many=True).data,
			"friends_recommendations": RecommendationSerializer(friends_recommendations, many=True).data,
			"friends_activity": friends_activity,
			"best_albums": TopAlbumSerializer(best_qs, many=True).data,
			"popular_albums": TopAlbumSerializer(popular_qs, many=True).data,
			"weekly_most_listened_albums": ListenedAlbumSerializer(weekly_most_listened_qs, many=True).data,
			"weekly_popular_albums": TopAlbumSerializer(weekly_popular_qs, many=True).data,
			"popular_reviews": PopularAlbumReviewSerializer(popular_reviews_qs, many=True).data,
			"anticipated_by_comments": AnticipatedAlbumSerializer(anticipated_qs, many=True).data,
			"new_releases": AlbumListSerializer(new_qs, many=True).data,
			"recent_albums": AlbumListSerializer(recent_qs, many=True).data,
			"top_albums_2025": TopAlbumSerializer(top_2025_qs, many=True).data,
			"trending_albums": TrendingAlbumSerializer(trending_albums, many=True).data,
			"trending_artists": TrendingArtistSerializer(trending_artists, many=True).data,
			"most_discussed_albums": MostDiscussedAlbumSerializer(most_discussed_albums, many=True).data,
		}
		return Response(payload)


class RecentAlbumsView(generics.ListAPIView):
	permission_classes = [AllowAny]
	serializer_class = AlbumListSerializer

	def get_queryset(self):
		limit_raw = str(self.request.query_params.get('limit', '')).strip()

		today = date.today()
		start = today - timedelta(days=7)

		qs = (
			Album.objects.select_related('artist')
			.prefetch_related('genres')
			.filter(
				is_approved=True,
				artist__is_approved=True,
				release_date__gt=start,
				release_date__lte=today,
			)
			.order_by('-release_date', 'title')
		)

		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 0
			if limit > 0:
				limit = min(limit, 50)
				qs = qs[:limit]

		return qs


class AnticipatedAlbumsView(generics.ListAPIView):
	permission_classes = [AllowAny]
	serializer_class = AnticipatedAlbumSerializer

	def get_queryset(self):
		limit_raw = str(self.request.query_params.get('limit', '')).strip()
		rank_raw = str(self.request.query_params.get('rank', '')).strip().lower()

		today = date.today()

		qs = (
			Album.objects.select_related('artist')
			.filter(is_approved=True, artist__is_approved=True, release_date__gt=today)
			.annotate(
				ratings_count=Count('ratings', distinct=True),
				reviews_count=Count('reviews', distinct=True),
			)
		)

		# Ranking modes:
		# - default: combined interest_score (ratings + reviews)
		# - rank=comments|reviews: sort by reviews_count only (treat reviews as comments)
		if rank_raw in ('comments', 'comment', 'reviews', 'review'):
			qs = qs.annotate(interest_score=F('reviews_count')).order_by('-reviews_count', 'release_date', 'title')
		else:
			qs = qs.annotate(interest_score=F('ratings_count') + F('reviews_count')).order_by('-interest_score', 'release_date', 'title')

		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 0
			if limit > 0:
				limit = min(limit, 50)
				qs = qs[:limit]

		return qs
