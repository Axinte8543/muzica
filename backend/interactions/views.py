import csv
import io
import json
import logging
import re
import time
import os
import urllib.request

from django.contrib.auth import get_user_model
from django.http import Http404
from django.http import HttpResponse
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.db import IntegrityError, transaction
from django.db.models import Avg, Case, Count, IntegerField, Max, Prefetch, Q, Sum, Value, When
from django.utils import timezone
from django.utils.text import slugify
from calendar import monthrange
from datetime import date, datetime, timedelta
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.authentication import JWTAuthentication

from music.models import Album, Song, Genre
from music.models import Artist
from music.pagination import AlbumRatingsPagination, SongRatingsPagination, WantToListenPagination

from users.models import UserPrivacySettings
from users.serializers import UserPrivacySettingsSerializer

from .models import (
 AlbumListen,
 AlbumLike,
 AlbumRating,
 AlbumReview,
 AlbumReviewDraft,
 AlbumReviewEdit,
 AlbumReviewLike,
 AlbumReviewReaction,
 AchievementUnlock,
 NotificationPreferences,
 ChatMessage,
 ChatTypingStatus,
 CatalogChangelogEvent,
 CorrectionReport,
  ReviewCommentEdit,
 SongLike,
 ArtistFollow,
 ArtistRating,
 FavoriteAlbum,
 FavoriteSong,
 FriendRequest,
 List,
 ListAlbum,
 ListAlbumNote,
 ListLike,
 ListMembership,
 ListTag,
 ModerationReport,
 MetadataSuggestion,
 ReviewComment,
 ReviewCommentMention,
 ReviewCommentReaction,
 SongComment,
  SongCommentMention,
 SongCommentEdit,
 SongCommentReaction,
 SongRating,
 UserActivity,
 SensitiveActionAudit,
 AnalyticsEvent,
 UserOnboarding,
 WantToListen,
)
from .serializers import (
 AlbumRatingSerializer,
 AlbumReviewCreateSerializer,
 AlbumReviewSerializer,
 AlbumReviewUpdateSerializer,
 AlbumReviewLikeNotificationSerializer,
 AlbumReleaseNotificationSerializer,
 AchievementUnlockNotificationSerializer,
 ArtistFollowNotificationSerializer,
 ArtistRatingSerializer,
 ReviewReplyNotificationSerializer,
 ReviewMentionNotificationSerializer,
 NotificationPreferencesSerializer,
 FriendRequestActionSerializer,
 FriendRequestCreateSerializer,
 FriendRequestSerializer,
 ReviewCommentCreateSerializer,
 ReviewCommentSerializer,
 ReviewCommentEditSerializer,
 ReviewCommentUpdateSerializer,
 AlbumReviewReactionSerializer,
 AlbumReviewReactionCreateSerializer,
 ReviewCommentReactionSerializer,
 ReviewCommentReactionCreateSerializer,
 SongCommentCreateSerializer,
 SongCommentSerializer,
 SongCommentEditSerializer,
 SongMentionNotificationSerializer,
 SongCommentReactionSerializer,
 SongCommentReactionCreateSerializer,
 ReactionsSummarySerializer,
  CatalogChangelogEventSerializer,
 FollowStatusSerializer,
 MyAlbumRatingSerializer,
 MyAlbumLikeSerializer,
 MyAlbumReviewSerializer,
 MyAlbumListenSerializer,
 MySongRatingSerializer,
 MyWantToListenSerializer,
 ListAlbumAddSerializer,
 ListAlbumNoteUpdateSerializer,
 ListCreateSerializer,
 ListCollaboratorRemoveSerializer,
 ListCollaboratorUpsertSerializer,
 ListRenameSerializer,
 ListReorderSerializer,
 ListSerializer,
 ListTagsUpdateSerializer,
 ListUpdateSerializer,
 FollowedArtistSerializer,
 FavoriteAlbumsUpdateSerializer,
 FavoriteAlbumItemSerializer,
 FavoriteSongsUpdateSerializer,
 FavoriteSongItemSerializer,
 PopularAlbumReviewSerializer,
 ProfileStatsSerializer,
 RatingInputSerializer,
 ChatMessageCreateSerializer,
 ChatMessageSerializer,
 ConversationSummarySerializer,
 ChatTypingStatusUpdateSerializer,
 CorrectionReportCreateSerializer,
 CorrectionReportSerializer,
 SongRatingSerializer,
 UserActivitySerializer,
 UserOnboardingCompleteSerializer,
 UserOnboardingSerializer,
 PublicListSerializer,
 ModerationReportCreateSerializer,
 ModerationReportSerializer,
 MetadataSuggestionCreateSerializer,
 MetadataSuggestionSerializer,
 AlbumReviewEditSerializer,
 AlbumReviewDraftSerializer,
 AlbumReviewDraftUpsertSerializer,
)

from .profile import favorite_albums_payload_for, favorite_songs_payload_for, profile_stats_payload_for
from .gamification import streak_payload_for, weekly_challenges_payload_for
from .recommender import invalidate_user_recommendations
try:
	import sentry_sdk
except Exception:
	sentry_sdk = None


def _create_activity(*, actor, activity_type: str, target_id=None, target_name: str = "", rating=None):
	UserActivity.objects.create(
	 actor=actor,
	 activity_type=activity_type,
	 target_id=target_id,
	 target_name=target_name or "",
	 rating=rating,
	)


def _audit_sensitive_action(*, actor, action_type: str, target_type: str, target_id=None, summary: str = '', metadata: dict | None = None):
	payload = {
	 'actor_id': getattr(actor, 'id', None),
	 'action_type': str(action_type or ''),
	 'target_type': str(target_type or ''),
	 'target_id': int(target_id) if target_id is not None else None,
	 'summary': str(summary or '')[:255],
	 'metadata': metadata or {},
	 'created_at': timezone.now().isoformat(),
	}
	SensitiveActionAudit.objects.create(
	 actor=actor,
	 action_type=action_type,
	 target_type=str(target_type or ''),
	 target_id=int(target_id) if target_id is not None else None,
	 summary=str(summary or '')[:255],
	 metadata=metadata or {},
	)
	_export_sensitive_audit_event(payload)
	if sentry_sdk:
		try:
			sentry_sdk.capture_message(
			 f"sensitive_audit:{action_type}",
			 level='info',
			)
			with sentry_sdk.push_scope() as scope:
				scope.set_tag('audit_action', str(action_type))
				scope.set_tag('audit_target_type', str(target_type or ''))
				if target_id is not None:
					scope.set_tag('audit_target_id', str(target_id))
				scope.set_extra('audit_summary', str(summary or '')[:1024])
				scope.set_extra('audit_metadata', metadata or {})
				sentry_sdk.capture_message(f"sensitive_audit_detail:{action_type}")
		except Exception:
			pass


def _export_sensitive_audit_event(payload: dict) -> None:

	export_url = str(os.environ.get('SECURITY_AUDIT_EXPORT_URL', '') or '').strip()
	stdout_enabled = str(os.environ.get('SECURITY_AUDIT_EXPORT_STDOUT', '') or '').strip().lower() in {'1', 'true', 'yes', 'on'}
	if not export_url and not stdout_enabled:
		return
	try:
		body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
		if export_url:
			req = urllib.request.Request(
			 export_url,
			 data=body,
			 headers={'Content-Type': 'application/json'},
			 method='POST',
			)
			with urllib.request.urlopen(req, timeout=3):
				pass
		elif stdout_enabled:
			print(json.dumps(payload, ensure_ascii=False), flush=True)
	except Exception:
		logging.exception('Failed to export sensitive audit event')


def _track_analytics_event(*, user, event_name: str, target_type: str = '', target_id=None, properties: dict | None = None):
	AnalyticsEvent.objects.create(
	 user=user,
	 event_name=str(event_name or ''),
	 target_type=str(target_type or ''),
	 target_id=int(target_id) if target_id is not None else None,
	 properties=properties or {},
	)


def _parse_days_window(raw_value: str, default: int = 30) -> int:
	text = str(raw_value or '').strip().lower()
	if not text:
		return int(default)
	if text.endswith('d'):
		text = text[:-1]
	try:
		return max(1, min(int(text), 365))
	except ValueError:
		return int(default)


def _analytics_metrics_for_window(*, days: int) -> dict:
	now = timezone.now()
	start = now - timedelta(days=max(1, int(days)))
	weekly_start = now - timedelta(days=7)
	events = AnalyticsEvent.objects.filter(created_at__gte=start).order_by('user_id', 'created_at', 'id')

	home_events = list(events.filter(event_name='home_view').values('user_id', 'created_at'))
	home_by_user: dict[int, list] = {}
	for row in home_events:
		uid = int(row['user_id'])
		home_by_user.setdefault(uid, []).append(row['created_at'])

	cohort_users = len(home_by_user)
	retained_d1 = 0
	retained_d7 = 0
	for timestamps in home_by_user.values():
		first_seen = timestamps[0]
		seen_dates = {ts.date() for ts in timestamps}
		if (first_seen + timedelta(days=1)).date() in seen_dates:
			retained_d1 += 1
		if (first_seen + timedelta(days=7)).date() in seen_dates:
			retained_d7 += 1

	review_events = list(events.filter(event_name='review_created').values('user_id', 'target_type', 'target_id'))
	review_user_ids = {int(row['user_id']) for row in review_events}
	review_count = len(review_events)
	comments_count = events.filter(event_name='review_comment_created').count()
	dm_opens = events.filter(event_name='dm_open').count()
	wau = AnalyticsEvent.objects.filter(created_at__gte=weekly_start).values('user_id').distinct().count()
	active_users = events.filter(event_name__in=['home_view', 'follow_artist', 'review_created', 'review_comment_created', 'dm_open']).values('user_id').distinct().count()

	avg_reviews_per_user = round(review_count / len(review_user_ids), 2) if review_user_ids else 0.0
	avg_comments_per_review = round(comments_count / review_count, 2) if review_count else 0.0
	retention_d1 = round((retained_d1 / cohort_users) * 100.0, 2) if cohort_users else 0.0
	retention_d7 = round((retained_d7 / cohort_users) * 100.0, 2) if cohort_users else 0.0

	from collections import defaultdict
	stage_times = defaultdict(dict)
	for row in events.filter(event_name__in=['onboarding_completed', 'follow_artist', 'review_created', 'review_comment_created']).values('user_id', 'event_name', 'created_at').order_by('user_id', 'created_at', 'id'):
		uid = int(row['user_id'])
		name = str(row['event_name'])
		if name not in stage_times[uid]:
			stage_times[uid][name] = row['created_at']

	funnel_onboarding = 0
	funnel_follow = 0
	funnel_review = 0
	funnel_comment = 0
	for user_stages in stage_times.values():
		ont = user_stages.get('onboarding_completed')
		flt = user_stages.get('follow_artist')
		rev = user_stages.get('review_created')
		com = user_stages.get('review_comment_created')
		if ont:
			funnel_onboarding += 1
		if ont and flt and flt >= ont:
			funnel_follow += 1
		if ont and flt and rev and flt >= ont and rev >= flt:
			funnel_review += 1
		if ont and flt and rev and com and flt >= ont and rev >= flt and com >= rev:
			funnel_comment += 1

	return {
	 'window_days': int(days),
	 'd1_retention_pct': retention_d1,
	 'd7_retention_pct': retention_d7,
	 'reviews_per_user': avg_reviews_per_user,
	 'comments_per_review': avg_comments_per_review,
	 'dm_opens': int(dm_opens),
	 'weekly_active_users': int(wau),
	 'active_users_7d': int(active_users),
	 'funnel': {
	  'onboarding_completed': int(funnel_onboarding),
	  'first_follow': int(funnel_follow),
	  'first_review': int(funnel_review),
	  'first_comment': int(funnel_comment),
	 },
	}


def _enforce_recent_action_limit(*, model, user, window_seconds: int, max_count: int, detail: str):
	cutoff = timezone.now() - timedelta(seconds=max(1, int(window_seconds)))
	recent_count = model.objects.filter(user=user, created_at__gte=cutoff).count()
	if recent_count >= max(1, int(max_count)):
		return Response(
		 {
		  "detail": detail,
		  "retry_after_seconds": max(1, int(window_seconds)),
		 },
		 status=status.HTTP_429_TOO_MANY_REQUESTS,
		)
	return None


def _public_lists_allowed_q(prefix: str = 'user'):
	return Q(**{f'{prefix}__privacy__public_lists': True}) | Q(**{f'{prefix}__privacy__isnull': True})


def _public_activity_allowed_q(prefix: str = 'actor'):
	return Q(**{f'{prefix}__privacy__public_activity': True}) | Q(**{f'{prefix}__privacy__isnull': True})


def _serialize_activity_feed(*, user, scope: str = 'all', limit: int = 50):
	limit = max(1, min(int(limit), 100))
	scope = str(scope or 'all').strip().lower()

	if scope == 'friends':
		accepted = FriendRequest.objects.select_related('sender', 'receiver').filter(
		 Q(sender=user) | Q(receiver=user),
		 status=FriendRequest.Status.ACCEPTED,
		)
		friend_ids: set[int] = set()
		for fr in accepted:
			other = fr.receiver if fr.sender_id == user.id else fr.sender
			friend_ids.add(int(other.id))

		if not friend_ids:
			return []

		qs = (
		 UserActivity.objects.select_related('actor')
		 .filter(actor_id__in=list(friend_ids))
		 .filter(_public_activity_allowed_q('actor'))
		 .order_by('-created_at')[:limit]
		)
		return UserActivitySerializer(qs, many=True).data

	if scope == 'following':
		followed_artist_ids = list(
		 ArtistFollow.objects.filter(user=user).values_list('artist_id', flat=True)
		)
		if not followed_artist_ids:
			return []

		followed_album_ids = list(
		 Album.objects.filter(
		  artist_id__in=followed_artist_ids,
		  is_approved=True,
		  artist__is_approved=True,
		 ).values_list('id', flat=True)
		)

		qs = (
		 UserActivity.objects.select_related('actor')
		 .exclude(actor=user)
		 .filter(_public_activity_allowed_q('actor'))
		 .filter(
		  Q(
		   activity_type=UserActivity.Type.FOLLOW_ARTIST,
		   target_id__in=followed_artist_ids,
		  )
		  | Q(
		   activity_type__in=[
		    UserActivity.Type.LISTEN_ALBUM,
		    UserActivity.Type.RATE_ALBUM,
		    UserActivity.Type.REVIEW_ALBUM,
		   ],
		   target_id__in=followed_album_ids,
		  )
		 )
		 .order_by('-created_at')[:limit]
		)
		return UserActivitySerializer(qs, many=True).data

	qs = (
	 UserActivity.objects.select_related('actor')
	 .exclude(actor=user)
	 .filter(_public_activity_allowed_q('actor'))
	 .order_by('-created_at')[:limit]
	)
	return UserActivitySerializer(qs, many=True).data


def _album_listen_album_filter():
	return (
	 Q(album__mb_primary_type__isnull=True)
	 |
	 Q(album__mb_primary_type='')
	 |
	 ~Q(album__mb_primary_type__iexact='single')
	)


def _with_album_listen_album_filter(qs):
	return (
	 qs
	 .filter(_album_listen_album_filter())
	 .annotate(
	  approved_tracks_count=Count(
	   'album__songs',
	   filter=Q(album__songs__is_approved=True),
	   distinct=True,
	  )
	 )
	 .exclude(approved_tracks_count=1)
	)


def _serialize_notifications_payload(*, user, limit: int = 20):
	prefs, _ = NotificationPreferences.objects.get_or_create(user=user)
	limit = max(1, min(int(limit), 50))

	incoming = []
	if prefs.notify_friend_requests:
		incoming = (
		 FriendRequest.objects.select_related('sender', 'receiver')
		 .filter(receiver=user, status=FriendRequest.Status.PENDING)
		 .order_by('-created_at')[:limit]
		)

	review_likes = []
	if prefs.notify_review_likes:
		review_likes = (
		 AlbumReviewLike.objects.select_related(
		  'user',
		  'review',
		  'review__album',
		  'review__album__artist',
		 )
		 .filter(review__user=user)
		 .exclude(user=user)
		 .order_by('-created_at')[:limit]
		)

	review_replies = []
	if prefs.notify_review_replies:
		review_replies = (
		 ReviewComment.objects.select_related(
		  'user',
		  'review',
		  'review__album',
		  'review__album__artist',
		 )
		 .filter(review__user=user)
		 .exclude(user=user)
		 .order_by('-created_at')[:limit]
		)

	mentions = []
	if getattr(prefs, 'notify_mentions', True):
		mentions = (
		 ReviewCommentMention.objects.select_related(
		  'comment',
		  'comment__user',
		  'comment__review',
		  'comment__review__album',
		  'comment__review__album__artist',
		  'mentioned_user',
		 )
		 .filter(mentioned_user=user)
		 .exclude(comment__user=user)
		 .order_by('-created_at')[:limit]
		)

	song_mentions = []
	if getattr(prefs, 'notify_mentions', True):
		song_mentions = (
		 SongCommentMention.objects.select_related(
		  'comment',
		  'comment__user',
		  'comment__song',
		  'comment__song__artist',
		  'mentioned_user',
		 )
		 .filter(mentioned_user=user)
		 .exclude(comment__user=user)
		 .order_by('-created_at')[:limit]
		)

	followed_artist_ids = list(
	 ArtistFollow.objects.filter(user=user).values_list('artist_id', flat=True)
	)

	artist_follows = []
	if getattr(prefs, 'notify_artist_follows', True) and followed_artist_ids:
		artist_follows = (
		 ArtistFollow.objects.select_related('user', 'artist')
		 .filter(artist_id__in=followed_artist_ids)
		 .exclude(user=user)
		 .order_by('-created_at')[:limit]
		)

	followed_artist_releases_payload = []
	if getattr(prefs, 'notify_followed_artist_releases', True) and followed_artist_ids:
		followed_albums = (
		 Album.objects.select_related('artist')
		 .filter(
		  artist_id__in=followed_artist_ids,
		  is_approved=True,
		  artist__is_approved=True,
		  release_date__lte=timezone.localdate(),
		 )
		 .order_by('-release_date', '-id')[:limit]
		)
		followed_artist_releases_payload = [
		 _album_release_payload(album=a, reason='followed_artist')
		 for a in followed_albums
		]

	preferred_genre_releases_payload = []
	if getattr(prefs, 'notify_genre_releases', True):
		preferred_genre_ids = _preferred_genre_ids_for_user(user=user, limit=5)
		if preferred_genre_ids:
			genre_albums = (
			 Album.objects.select_related('artist')
			 .prefetch_related('genres')
			 .filter(
			  genres__id__in=preferred_genre_ids,
			  is_approved=True,
			  artist__is_approved=True,
			  release_date__lte=timezone.localdate(),
			 )
			 .distinct()
			 .order_by('-release_date', '-id')[:limit]
			)
			preferred_set = set(int(x) for x in preferred_genre_ids)
			for album in genre_albums:
				matched_genres = [
				 g.name
				 for g in album.genres.all()
				 if int(g.id) in preferred_set
				]
				preferred_genre_releases_payload.append(
				 _album_release_payload(
				  album=album,
				  reason='preferred_genres',
				  matched_genres=matched_genres,
				 )
				)

	achievement_unlocks = []
	if getattr(prefs, 'notify_achievement_unlocks', True):
		achievement_unlocks = (
		 AchievementUnlock.objects.filter(user=user)
		 .order_by('-created_at')[:limit]
		)

	return {
	 "incoming_friend_requests": FriendRequestSerializer(incoming, many=True).data,
	 "review_likes": AlbumReviewLikeNotificationSerializer(review_likes, many=True).data,
	 "review_replies": ReviewReplyNotificationSerializer(review_replies, many=True).data,
	 "mentions": ReviewMentionNotificationSerializer(mentions, many=True).data,
	 "song_mentions": SongMentionNotificationSerializer(song_mentions, many=True).data,
	 "artist_follows": ArtistFollowNotificationSerializer(artist_follows, many=True).data,
	 "followed_artist_releases": AlbumReleaseNotificationSerializer(followed_artist_releases_payload, many=True).data,
	 "preferred_genre_releases": AlbumReleaseNotificationSerializer(preferred_genre_releases_payload, many=True).data,
	 "achievement_unlocks": AchievementUnlockNotificationSerializer(achievement_unlocks, many=True).data,
	}


def _get_user_from_live_token(raw_token: str):
	token = str(raw_token or '').strip()
	if not token:
		return None

	auth = JWTAuthentication()
	try:
		validated = auth.get_validated_token(token)
		return auth.get_user(validated)
	except Exception:
		return None


def _sse_event(event: str, payload: dict) -> str:
	return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


_MENTION_RE = re.compile(r'@([A-Za-z0-9_]{1,150})')


def _extract_mentioned_usernames(text: str) -> set[str]:
	value = str(text or '')
	return {m.group(1) for m in _MENTION_RE.finditer(value) if m and m.group(1)}


def _sync_review_comment_mentions(*, comment: ReviewComment):
	usernames = _extract_mentioned_usernames(comment.content)
	ReviewCommentMention.objects.filter(comment=comment).delete()
	if not usernames:
		return

	User = get_user_model()
	mentioned_users = list(User.objects.filter(username__in=list(usernames)))
	mentioned_users = [u for u in mentioned_users if int(u.id) != int(comment.user_id)]
	if not mentioned_users:
		return

	ReviewCommentMention.objects.bulk_create(
	 [
	  ReviewCommentMention(comment=comment, mentioned_user=u)
	  for u in mentioned_users
	 ],
	 ignore_conflicts=True,
	)


def _sync_song_comment_mentions(*, comment: SongComment):
	usernames = _extract_mentioned_usernames(comment.content)
	SongCommentMention.objects.filter(comment=comment).delete()
	if not usernames:
		return

	User = get_user_model()
	mentioned_users = list(User.objects.filter(username__in=list(usernames)))
	mentioned_users = [u for u in mentioned_users if int(u.id) != int(comment.user_id)]
	if not mentioned_users:
		return

	SongCommentMention.objects.bulk_create(
	 [
	  SongCommentMention(comment=comment, mentioned_user=u)
	  for u in mentioned_users
	 ],
	 ignore_conflicts=True,
	)


def _preferred_genre_ids_for_user(*, user, limit: int = 5) -> list[int]:
                                                                    
	listen_rows = (
	 AlbumListen.objects.filter(
	  user=user,
	  album__is_approved=True,
	  album__artist__is_approved=True,
	 )
	 .values('album__genres__id')
	 .exclude(album__genres__id__isnull=True)
	 .annotate(c=Count('id'))
	)
	rating_rows = (
	 AlbumRating.objects.filter(
	  user=user,
	  album__is_approved=True,
	  album__artist__is_approved=True,
	 )
	 .values('album__genres__id')
	 .exclude(album__genres__id__isnull=True)
	 .annotate(c=Count('id'))
	)

	scores: dict[int, int] = {}
	for row in listen_rows:
		gid = row.get('album__genres__id')
		if gid is None:
			continue
		scores[int(gid)] = int(scores.get(int(gid), 0)) + int(row.get('c') or 0)
	for row in rating_rows:
		gid = row.get('album__genres__id')
		if gid is None:
			continue
		scores[int(gid)] = int(scores.get(int(gid), 0)) + int(row.get('c') or 0) * 2

	ordered = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
	return [int(gid) for gid, _score in ordered[: max(1, int(limit))]]


def _album_release_payload(*, album: Album, reason: str, matched_genres: list[str] | None = None) -> dict:
	payload = {
	 'album_id': int(album.id),
	 'album_title': album.title,
	 'album_slug': album.slug,
	 'artist_id': int(album.artist_id),
	 'artist_name': album.artist.name,
	 'artist_slug': album.artist.slug,
	 'release_date': album.release_date,
	 'created_at': album.created_at,
	 'reason': reason,
	}
	if matched_genres:
		payload['matched_genres'] = [str(g) for g in matched_genres if str(g).strip()]
	return payload


def _parse_bool(value, *, default: bool = False) -> bool:
	if value is None:
		return bool(default)
	v = str(value).strip().lower()
	if v in {'1', 'true', 'yes', 'on'}:
		return True
	if v in {'0', 'false', 'no', 'off'}:
		return False
	return bool(default)


def _personalized_release_payloads(
 *,
 user,
 from_date: date | None,
 to_date: date | None,
 limit: int = 200,
 include_followed_artists: bool = True,
 include_preferred_genres: bool = True,
) -> list[dict]:
	followed_artist_ids: list[int] = []
	preferred_genre_ids: list[int] = []

	if include_followed_artists:
		followed_artist_ids = list(
		 ArtistFollow.objects.filter(user=user).values_list('artist_id', flat=True)
		)

	if include_preferred_genres:
		preferred_genre_ids = _preferred_genre_ids_for_user(user=user, limit=5)

	if not followed_artist_ids and not preferred_genre_ids:
		return []

	query = Q()
	if followed_artist_ids:
		query |= Q(artist_id__in=followed_artist_ids)
	if preferred_genre_ids:
		query |= Q(genres__id__in=preferred_genre_ids)

	albums = (
	 Album.objects.select_related('artist')
	 .prefetch_related('genres')
	 .filter(
	  query,
	  is_approved=True,
	  artist__is_approved=True,
	 )
	 .distinct()
	)

	if from_date is not None:
		albums = albums.filter(release_date__gte=from_date)
	if to_date is not None:
		albums = albums.filter(release_date__lte=to_date)

	albums = albums.order_by('release_date', 'id')[: max(1, min(int(limit), 500))]

	followed_set = {int(aid) for aid in followed_artist_ids}
	preferred_set = {int(gid) for gid in preferred_genre_ids}

	payloads: list[dict] = []
	for album in albums:
		from_followed_artist = int(album.artist_id) in followed_set
		matched_genres = [
		 g.name
		 for g in album.genres.all()
		 if int(g.id) in preferred_set
		]
		from_preferred_genre = bool(matched_genres)

		if not from_followed_artist and not from_preferred_genre:
			continue

		reason = 'followed_artist' if from_followed_artist else 'preferred_genres'
		payloads.append(
		 _album_release_payload(
		  album=album,
		  reason=reason,
		  matched_genres=matched_genres if from_preferred_genre else None,
		 )
		)

	return payloads


class AlbumRateView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, album_id: int):
		album = get_object_or_404(Album, pk=album_id, is_approved=True, artist__is_approved=True)
		rating_obj = AlbumRating.objects.filter(user=request.user, album=album).first()

		if not rating_obj:
			return Response({"rating": None}, status=status.HTTP_200_OK)

		output = AlbumRatingSerializer(rating_obj).data
		return Response(output, status=status.HTTP_200_OK)

	def post(self, request, album_id: int):
		serializer = RatingInputSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		album = get_object_or_404(Album, pk=album_id, is_approved=True, artist__is_approved=True)
		new_rating = serializer.validated_data["rating"]
		existing = AlbumRating.objects.filter(user=request.user, album=album).first()
		prev_rating = int(existing.rating) if existing else None

		rating_obj, created = AlbumRating.objects.update_or_create(
		 user=request.user,
		 album=album,
		 defaults={"rating": new_rating},
		)

		if created or prev_rating != new_rating:
			_create_activity(
			 actor=request.user,
			 activity_type=UserActivity.Type.RATE_ALBUM,
			 target_id=album.id,
			 target_name=album.title,
			 rating=int(new_rating),
			)
			invalidate_user_recommendations(request.user.id)

		output = AlbumRatingSerializer(rating_obj).data
		return Response(
		 output,
		 status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
		)


class ArtistRateView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, artist_id: int):
		artist = get_object_or_404(Artist, pk=artist_id, is_approved=True)
		rating_obj = ArtistRating.objects.filter(user=request.user, artist=artist).first()

		if not rating_obj:
			return Response({"rating": None}, status=status.HTTP_200_OK)

		output = ArtistRatingSerializer(rating_obj).data
		return Response(output, status=status.HTTP_200_OK)

	def post(self, request, artist_id: int):
		serializer = RatingInputSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		artist = get_object_or_404(Artist, pk=artist_id, is_approved=True)
		new_rating = serializer.validated_data["rating"]

		rating_obj, created = ArtistRating.objects.update_or_create(
		 user=request.user,
		 artist=artist,
		 defaults={"rating": new_rating},
		)

		output = ArtistRatingSerializer(rating_obj).data
		return Response(
		 output,
		 status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
		)


class SongRateView(APIView):
	permission_classes = [IsAuthenticated]

	def _get_song_or_404(self, *, song_id: int):
		qs = (
		 Song.objects.select_related('artist', 'album')
		 .filter(is_approved=True, artist__is_approved=True)
		 .filter(Q(album__isnull=True) | Q(album__is_approved=True, album__artist__is_approved=True))
		)
		return get_object_or_404(qs, pk=song_id)

	def get(self, request, song_id: int):
		song = self._get_song_or_404(song_id=song_id)
		rating_obj = SongRating.objects.filter(user=request.user, song=song).first()

		if not rating_obj:
			return Response({"rating": None}, status=status.HTTP_200_OK)

		output = SongRatingSerializer(rating_obj).data
		return Response(output, status=status.HTTP_200_OK)

	def post(self, request, song_id: int):
		serializer = RatingInputSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		song = self._get_song_or_404(song_id=song_id)

		rating_obj, created = SongRating.objects.update_or_create(
		 user=request.user,
		 song=song,
		 defaults={"rating": serializer.validated_data["rating"]},
		)

		output = SongRatingSerializer(rating_obj).data
		return Response(
		 output,
		 status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
		)

class PublicListsView(APIView):
	permission_classes = [AllowAny]

	def get(self, request):
		limit_raw = str(request.query_params.get('limit', '')).strip()
		page_raw = str(request.query_params.get('page', '')).strip()
		page_size_raw = str(request.query_params.get('page_size', '')).strip()
		sort_raw = str(request.query_params.get('sort', '')).strip().lower()
		tag_raw = str(request.query_params.get('tag', '')).strip()
		limit = 20
		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 20
		limit = max(1, min(limit, 50))
		page = None
		page_size = limit
		if page_raw:
			try:
				page = int(page_raw)
			except ValueError:
				return Response({"detail": "Invalid page"}, status=status.HTTP_400_BAD_REQUEST)
			page = max(1, page)
			if page_size_raw:
				try:
					page_size = int(page_size_raw)
				except ValueError:
					return Response({"detail": "Invalid page_size"}, status=status.HTTP_400_BAD_REQUEST)
			page_size = max(1, min(page_size, 50))
		sort_by = sort_raw if sort_raw in {'new', 'liked'} else 'new'
		tag_name = ' '.join(tag_raw.split()) if tag_raw else ''

		qs = (
		 List.objects.select_related('user')
		 .filter(is_public=True)
		 .filter(_public_lists_allowed_q('user'))
		 .prefetch_related('tags')
		 .annotate(
		  albums_count=Count('albums', distinct=True),
		  likes_count=Count('likes', distinct=True),
		 )
		)
		if tag_name:
			qs = qs.filter(tags__name__iexact=tag_name).distinct()
		if sort_by == 'liked':
			qs = qs.order_by('-likes_count', '-created_at', '-id')
		else:
			qs = qs.order_by('-created_at', '-id')

		total_count = None
		if page is not None:
			total_count = qs.count()
			start = (page - 1) * page_size
			stop = start + page_size
			lists = list(qs[start:stop])
		else:
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
		  "tags": [t.name for t in l.tags.all()],
		  "is_liked": bool(l.id in liked_ids) if request.user.is_authenticated else False,
		 }
		 for l in lists
		]
		results = PublicListSerializer(payload, many=True).data
		if page is not None:
			assert total_count is not None
			next_page = page + 1 if page * page_size < total_count else None
			previous_page = page - 1 if page > 1 else None
			return Response(
			 {
			  "count": int(total_count),
			  "page": int(page),
			  "page_size": int(page_size),
			  "next": next_page,
			  "previous": previous_page,
			  "results": results,
			 },
			 status=status.HTTP_200_OK,
			)
		return Response(results, status=status.HTTP_200_OK)


class PublicListDetailView(APIView):
	permission_classes = [AllowAny]

	def get(self, request, list_id: int):
		list_qs = (
		 List.objects.select_related('user')
		 .filter(pk=list_id, is_public=True)
		 .filter(_public_lists_allowed_q('user'))
		 .prefetch_related('tags', 'list_albums__album__artist')
		 .annotate(
		  albums_count=Count('albums', distinct=True),
		  likes_count=Count('likes', distinct=True),
		 )
		)
		list_obj = get_object_or_404(list_qs)

		is_liked = False
		if request.user.is_authenticated:
			is_liked = ListLike.objects.filter(user=request.user, list=list_obj).exists()

		items = list(list_obj.list_albums.all())
		items.sort(key=lambda x: (int(getattr(x, 'position', 0) or 0), int(x.id)))

		albums_payload = [
		 {
		  'id': int(item.id),
		  'album_id': int(item.album_id),
		  'album_title': item.album.title,
		  'album_slug': item.album.slug,
		  'artist_name': item.album.artist.name,
		  'artist_slug': item.album.artist.slug,
		  'cover_url': item.album.cover_url,
		  'release_date': item.album.release_date,
		  'position': int(getattr(item, 'position', 0) or 0),
		  'added_at': item.added_at,
		 }
		 for item in items
		]

		payload = {
		 'id': int(list_obj.id),
		 'name': list_obj.name,
		 'description': list_obj.description or '',
		 'user_username': list_obj.user.username,
		 'created_at': list_obj.created_at,
		 'updated_at': list_obj.updated_at,
		 'albums_count': int(getattr(list_obj, 'albums_count', 0) or 0),
		 'likes_count': int(getattr(list_obj, 'likes_count', 0) or 0),
		 'is_liked': bool(is_liked),
		 'tags': [t.name for t in list_obj.tags.all()],
		 'albums': albums_payload,
		}

		return Response(payload, status=status.HTTP_200_OK)


class ListLikeView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, list_id: int):
		list_qs = List.objects.select_related('user').filter(pk=list_id, is_public=True).filter(
		 _public_lists_allowed_q('user'),
		)
		list_obj = get_object_or_404(list_qs)
		ListLike.objects.get_or_create(user=request.user, list=list_obj)
		likes_count = ListLike.objects.filter(list=list_obj).count()
		return Response({"liked": True, "likes_count": likes_count}, status=status.HTTP_200_OK)

	def delete(self, request, list_id: int):
		list_qs = List.objects.select_related('user').filter(pk=list_id, is_public=True).filter(
		 _public_lists_allowed_q('user'),
		)
		list_obj = get_object_or_404(list_qs)
		ListLike.objects.filter(user=request.user, list=list_obj).delete()
		likes_count = ListLike.objects.filter(list=list_obj).count()
		return Response({"liked": False, "likes_count": likes_count}, status=status.HTTP_200_OK)


class AlbumReviewsView(APIView):
	def get_permissions(self):
		if self.request.method == "GET":
			return [AllowAny()]
		return [IsAuthenticated()]

	def get(self, request, album_id: int):
		album = get_object_or_404(Album, pk=album_id, is_approved=True, artist__is_approved=True)
		reviews = (
		 AlbumReview.objects.select_related("user")
		 .filter(album=album)
		 .annotate(likes_count=Count('likes'))
		 .order_by("-created_at")
		)
		output = AlbumReviewSerializer(reviews, many=True).data
		return Response(output, status=status.HTTP_200_OK)

	def post(self, request, album_id: int):
		serializer = AlbumReviewCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		album = get_object_or_404(Album, pk=album_id, is_approved=True, artist__is_approved=True)

		review = AlbumReview.objects.create(
		 user=request.user,
		 album=album,
		 title=serializer.validated_data.get("title", ""),
		 content=serializer.validated_data["content"],
		)
		AlbumReviewDraft.objects.filter(user=request.user, album=album).delete()
		_create_activity(
		 actor=request.user,
		 activity_type=UserActivity.Type.REVIEW_ALBUM,
		 target_id=album.id,
		 target_name=album.title,
		)
		_track_analytics_event(
		 user=request.user,
		 event_name='review_created',
		 target_type='album',
		 target_id=album.id,
		 properties={'album_slug': album.slug, 'artist_id': int(album.artist_id)},
		)
		output = AlbumReviewSerializer(review).data
		return Response(output, status=status.HTTP_201_CREATED)


class AlbumReviewDetailView(APIView):
	permission_classes = [IsAuthenticated]

	def put(self, request, review_id: int):
		serializer = AlbumReviewUpdateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		review = get_object_or_404(
		 AlbumReview.objects.select_related('album', 'album__artist', 'user'),
		 pk=review_id,
		)
		if review.user_id != request.user.id:
			return Response(status=status.HTTP_403_FORBIDDEN)
		if not review.album.is_approved or not review.album.artist.is_approved:
			return Response(status=status.HTTP_404_NOT_FOUND)

		new_title = serializer.validated_data.get('title', '')
		new_content = serializer.validated_data['content']
		prev_title = review.title
		prev_content = review.content
		if prev_title != new_title or prev_content != new_content:
			AlbumReviewEdit.objects.create(
			 review=review,
			 edited_by=request.user,
			 previous_title=prev_title or '',
			 previous_content=prev_content or '',
			)
		review.title = new_title
		review.content = new_content
		review.save(update_fields=['title', 'content', 'updated_at'])

		output = AlbumReviewSerializer(review).data
		return Response(output, status=status.HTTP_200_OK)

	def delete(self, request, review_id: int):
		review = get_object_or_404(
		 AlbumReview.objects.select_related('album', 'album__artist', 'user'),
		 pk=review_id,
		)
		if review.user_id != request.user.id:
			return Response(status=status.HTTP_403_FORBIDDEN)
		if not review.album.is_approved or not review.album.artist.is_approved:
			return Response(status=status.HTTP_404_NOT_FOUND)

		review.delete()
		return Response(status=status.HTTP_204_NO_CONTENT)


class ReviewCommentsView(APIView):
	def get_permissions(self):
		if self.request.method == "GET":
			return [AllowAny()]
		return [IsAuthenticated()]

	def _get_review_or_404(self, *, review_id: int):
		return get_object_or_404(
		 AlbumReview.objects.select_related('album', 'album__artist'),
		 pk=review_id,
		 album__is_approved=True,
		 album__artist__is_approved=True,
		)

	def get(self, request, review_id: int):
		review = self._get_review_or_404(review_id=review_id)
		comments = (
		 ReviewComment.objects.select_related('user')
		 .filter(review=review)
		 .order_by('created_at', 'id')
		)
		output = ReviewCommentSerializer(comments, many=True).data
		return Response(output, status=status.HTTP_200_OK)

	def post(self, request, review_id: int):
		serializer = ReviewCommentCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		limited = _enforce_recent_action_limit(
		 model=ReviewComment,
		 user=request.user,
		 window_seconds=45,
		 max_count=6,
		 detail='Too many comments. Please wait a moment and try again.',
		)
		if limited:
			return limited

		review = self._get_review_or_404(review_id=review_id)
		parent = None
		parent_id = serializer.validated_data.get('parent_id')
		if parent_id:
			parent = get_object_or_404(
			 ReviewComment.objects.select_related('review'),
			 pk=parent_id,
			)
			if parent.review_id != review.id:
				return Response({"detail": "parent_id must belong to the same review"}, status=status.HTTP_400_BAD_REQUEST)

		comment = ReviewComment.objects.create(
		 user=request.user,
		 review=review,
		 parent=parent,
		 content=serializer.validated_data['content'],
		)
		_sync_review_comment_mentions(comment=comment)
		_audit_sensitive_action(
		 actor=request.user,
		 action_type=SensitiveActionAudit.ActionType.COMMENT_CREATED,
		 target_type='review_comment',
		 target_id=comment.id,
		 summary='Review comment created',
		 metadata={'review_id': int(review.id), 'parent_id': int(parent.id) if parent else None},
		)
		_track_analytics_event(
		 user=request.user,
		 event_name='review_comment_created',
		 target_type='review',
		 target_id=review.id,
		 properties={'comment_id': int(comment.id), 'parent_id': int(parent.id) if parent else None},
		)
		output = ReviewCommentSerializer(comment).data
		return Response(output, status=status.HTTP_201_CREATED)


class ReviewCommentDetailView(APIView):
	permission_classes = [IsAuthenticated]

	def _get_comment_or_404(self, *, comment_id: int):
		return get_object_or_404(
		 ReviewComment.objects.select_related(
		  'user',
		  'review',
		  'review__album',
		  'review__album__artist',
		 ),
		 pk=comment_id,
		 review__album__is_approved=True,
		 review__album__artist__is_approved=True,
		)

	def put(self, request, comment_id: int):
		serializer = ReviewCommentUpdateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		comment = self._get_comment_or_404(comment_id=comment_id)
		if comment.user_id != request.user.id:
			return Response(status=status.HTTP_403_FORBIDDEN)

		new_content = serializer.validated_data['content']
		if new_content != comment.content:
			ReviewCommentEdit.objects.create(
			 comment=comment,
			 edited_by=request.user,
			 previous_content=comment.content or '',
			)
			comment.content = new_content
			comment.save(update_fields=['content', 'updated_at'])
		_sync_review_comment_mentions(comment=comment)
		_audit_sensitive_action(
		 actor=request.user,
		 action_type=SensitiveActionAudit.ActionType.COMMENT_EDITED,
		 target_type='review_comment',
		 target_id=comment.id,
		 summary='Review comment edited',
		 metadata={'review_id': int(comment.review_id)},
		)
		output = ReviewCommentSerializer(comment).data
		return Response(output, status=status.HTTP_200_OK)

	def delete(self, request, comment_id: int):
		comment = self._get_comment_or_404(comment_id=comment_id)
		if comment.user_id != request.user.id:
			return Response(status=status.HTTP_403_FORBIDDEN)
		comment.delete()
		return Response(status=status.HTTP_204_NO_CONTENT)


class ReviewCommentHistoryView(APIView):
	permission_classes = [AllowAny]

	def get(self, request, comment_id: int):
		comment = get_object_or_404(
		 ReviewComment.objects.select_related('review', 'review__album', 'review__album__artist'),
		 pk=comment_id,
		 review__album__is_approved=True,
		 review__album__artist__is_approved=True,
		)
		edits = ReviewCommentEdit.objects.select_related('edited_by').filter(comment=comment).order_by('-edited_at', '-id')[:50]
		return Response(ReviewCommentEditSerializer(edits, many=True).data, status=status.HTTP_200_OK)


class SongCommentDetailView(APIView):
	permission_classes = [IsAuthenticated]

	def _get_comment_or_404(self, *, comment_id: int):
		return get_object_or_404(
		 SongComment.objects.select_related('user', 'song', 'song__artist', 'song__album', 'song__album__artist'),
		 pk=comment_id,
		 song__is_approved=True,
		 song__artist__is_approved=True,
		)

	def put(self, request, comment_id: int):
		serializer = SongCommentCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		comment = self._get_comment_or_404(comment_id=comment_id)
		if comment.user_id != request.user.id:
			return Response(status=status.HTTP_403_FORBIDDEN)

		new_content = serializer.validated_data['content']
		if new_content != comment.content:
			SongCommentEdit.objects.create(
			 comment=comment,
			 edited_by=request.user,
			 previous_content=comment.content or '',
			)
			comment.content = new_content
			comment.save(update_fields=['content', 'updated_at'])
		_audit_sensitive_action(
		 actor=request.user,
		 action_type=SensitiveActionAudit.ActionType.COMMENT_EDITED,
		 target_type='song_comment',
		 target_id=comment.id,
		 summary='Song comment edited',
		 metadata={'song_id': int(comment.song_id)},
		)

		return Response(SongCommentSerializer(comment).data, status=status.HTTP_200_OK)

	def delete(self, request, comment_id: int):
		comment = self._get_comment_or_404(comment_id=comment_id)
		if comment.user_id != request.user.id:
			return Response(status=status.HTTP_403_FORBIDDEN)
		comment.delete()
		return Response(status=status.HTTP_204_NO_CONTENT)


class SongCommentHistoryView(APIView):
	permission_classes = [AllowAny]

	def get(self, request, comment_id: int):
		comment = get_object_or_404(
		 SongComment.objects.select_related('song', 'song__artist', 'song__album', 'song__album__artist'),
		 pk=comment_id,
		 song__is_approved=True,
		 song__artist__is_approved=True,
		)
		edits = SongCommentEdit.objects.select_related('edited_by').filter(comment=comment).order_by('-edited_at', '-id')[:50]
		return Response(SongCommentEditSerializer(edits, many=True).data, status=status.HTTP_200_OK)


class SongCommentsView(APIView):
	def get_permissions(self):
		if self.request.method == "GET":
			return [AllowAny()]
		return [IsAuthenticated()]

	def _get_song_or_404(self, *, song_id: int):
		return get_object_or_404(
		 Song.objects.select_related('artist', 'album'),
		 pk=song_id,
		 is_approved=True,
		 artist__is_approved=True,
		)

	def get(self, request, song_id: int):
		song = self._get_song_or_404(song_id=song_id)
		comments = (
		 SongComment.objects.select_related('user')
		 .filter(song=song)
		 .order_by('created_at', 'id')
		)
		output = SongCommentSerializer(comments, many=True).data
		return Response(output, status=status.HTTP_200_OK)

	def post(self, request, song_id: int):
		serializer = SongCommentCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		limited = _enforce_recent_action_limit(
		 model=SongComment,
		 user=request.user,
		 window_seconds=45,
		 max_count=6,
		 detail='Too many comments. Please wait a moment and try again.',
		)
		if limited:
			return limited

		song = self._get_song_or_404(song_id=song_id)
		parent = None
		parent_id = serializer.validated_data.get('parent_id')
		if parent_id:
			parent = get_object_or_404(
			 SongComment.objects.select_related('song'),
			 pk=parent_id,
			)
			if parent.song_id != song.id:
				return Response({"detail": "parent_id must belong to the same song"}, status=status.HTTP_400_BAD_REQUEST)

		comment = SongComment.objects.create(
		 user=request.user,
		 song=song,
		 parent=parent,
		 content=serializer.validated_data['content'],
		)
		_sync_song_comment_mentions(comment=comment)
		_audit_sensitive_action(
		 actor=request.user,
		 action_type=SensitiveActionAudit.ActionType.COMMENT_CREATED,
		 target_type='song_comment',
		 target_id=comment.id,
		 summary='Song comment created',
		 metadata={'song_id': int(song.id), 'parent_id': int(parent.id) if parent else None},
		)
		_track_analytics_event(
		 user=request.user,
		 event_name='song_comment_created',
		 target_type='song',
		 target_id=song.id,
		 properties={'comment_id': int(comment.id), 'parent_id': int(parent.id) if parent else None},
		)
		output = SongCommentSerializer(comment).data
		return Response(output, status=status.HTTP_201_CREATED)


class PopularReviewsView(APIView):
	permission_classes = [AllowAny]

	def get(self, request):
		limit_raw = str(request.query_params.get('limit', '')).strip()
		days_raw = str(request.query_params.get('days', '')).strip()
		limit = 10
		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 10
		limit = max(1, min(limit, 50))

		days = 7
		if days_raw:
			try:
				days = int(days_raw)
			except ValueError:
				days = 7
		days = max(0, min(days, 365))
		since = timezone.now() - timedelta(days=days) if days > 0 else None

		qs = (
		 AlbumReview.objects.select_related('user', 'album', 'album__artist')
		 .filter(album__is_approved=True, album__artist__is_approved=True)
		)
		if since is not None:
			qs = qs.annotate(
			 likes_count=Count('likes', filter=Q(likes__created_at__gte=since), distinct=True),
			)
		else:
			qs = qs.annotate(likes_count=Count('likes'))

		reviews = qs.order_by('-likes_count', '-created_at')[:limit]

		output = PopularAlbumReviewSerializer(reviews, many=True).data
		return Response(output, status=status.HTTP_200_OK)


class AlbumReviewLikeView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, review_id: int):
		review = get_object_or_404(
		 AlbumReview.objects.select_related('album', 'album__artist'),
		 pk=review_id,
		 album__is_approved=True,
		 album__artist__is_approved=True,
		)
		AlbumReviewLike.objects.get_or_create(user=request.user, review=review)
		likes_count = AlbumReviewLike.objects.filter(review=review).count()
		return Response({"liked": True, "likes_count": likes_count}, status=status.HTTP_200_OK)

	def delete(self, request, review_id: int):
		review = get_object_or_404(
		 AlbumReview.objects.select_related('album', 'album__artist'),
		 pk=review_id,
		 album__is_approved=True,
		 album__artist__is_approved=True,
		)
		AlbumReviewLike.objects.filter(user=request.user, review=review).delete()
		likes_count = AlbumReviewLike.objects.filter(review=review).count()
		return Response({"liked": False, "likes_count": likes_count}, status=status.HTTP_200_OK)


class AlbumReviewReactionsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, review_id):
		review = get_object_or_404(
		 AlbumReview.objects.select_related('album', 'album__artist'),
		 pk=review_id,
		 album__is_approved=True,
		 album__artist__is_approved=True,
		)

		reactions = AlbumReviewReaction.objects.filter(review=review).values('emoji').annotate(count=Count('id'))

		user_reactions = set(
		 AlbumReviewReaction.objects.filter(
		  review=review,
		  user=request.user,
		 ).values_list('emoji', flat=True)
		)

		result = []
		for reaction in reactions:
			result.append({
			 'emoji': reaction['emoji'],
			 'count': reaction['count'],
			 'user_reacted': reaction['emoji'] in user_reactions,
			})

		serializer = ReactionsSummarySerializer(result, many=True)
		return Response(serializer.data, status=status.HTTP_200_OK)


class AlbumReviewReactionView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, review_id):
		review = get_object_or_404(
		 AlbumReview.objects.select_related('album', 'album__artist'),
		 pk=review_id,
		 album__is_approved=True,
		 album__artist__is_approved=True,
		)

		serializer = AlbumReviewReactionCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		emoji = serializer.validated_data['emoji']

		reaction, created = AlbumReviewReaction.objects.get_or_create(
		 user=request.user,
		 review=review,
		 emoji=emoji,
		)

		if not created:
			reaction.delete()
			return Response({'detail': 'Reaction removed'}, status=status.HTTP_200_OK)

		return Response(AlbumReviewReactionSerializer(reaction).data, status=status.HTTP_201_CREATED)


class AlbumListenView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, album_id: int):
		album = get_object_or_404(Album, pk=album_id, is_approved=True, artist__is_approved=True)
		today = timezone.localdate()
		listened_today = AlbumListen.objects.filter(user=request.user, album=album, listened_date=today).exists()
		return Response({"listened_today": listened_today}, status=status.HTTP_200_OK)

	def post(self, request, album_id: int):
		album = get_object_or_404(Album, pk=album_id, is_approved=True, artist__is_approved=True)
		today = timezone.localdate()
		_, created = AlbumListen.objects.get_or_create(
		 user=request.user,
		 album=album,
		 listened_date=today,
		)
		if created:
			_create_activity(
			 actor=request.user,
			 activity_type=UserActivity.Type.LISTEN_ALBUM,
			 target_id=album.id,
			 target_name=album.title,
			)
		WantToListen.objects.filter(user=request.user, album=album).delete()
		return Response(
		 {"listened_today": True, "created": created},
		 status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
		)


class AlbumWantToListenView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, album_id: int):
		album = get_object_or_404(Album, pk=album_id, is_approved=True, artist__is_approved=True)
		wanted = WantToListen.objects.filter(user=request.user, album=album).exists()
		return Response({"wanted": wanted}, status=status.HTTP_200_OK)

	def post(self, request, album_id: int):
		album = get_object_or_404(Album, pk=album_id, is_approved=True, artist__is_approved=True)
		_, created = WantToListen.objects.get_or_create(user=request.user, album=album)
		return Response(
		 {"wanted": True, "created": created},
		 status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
		)

	def delete(self, request, album_id: int):
		album = get_object_or_404(Album, pk=album_id, is_approved=True, artist__is_approved=True)
		WantToListen.objects.filter(user=request.user, album=album).delete()
		return Response({"wanted": False}, status=status.HTTP_200_OK)


class AlbumLikeView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, album_id: int):
		album = get_object_or_404(Album, pk=album_id, is_approved=True, artist__is_approved=True)
		liked = AlbumLike.objects.filter(user=request.user, album=album).exists()
		likes_count = AlbumLike.objects.filter(album=album).count()
		return Response({"liked": liked, "likes_count": likes_count}, status=status.HTTP_200_OK)

	def post(self, request, album_id: int):
		album = get_object_or_404(Album, pk=album_id, is_approved=True, artist__is_approved=True)
		_, created = AlbumLike.objects.get_or_create(user=request.user, album=album)
		likes_count = AlbumLike.objects.filter(album=album).count()
		return Response(
		 {"liked": True, "created": created, "likes_count": likes_count},
		 status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
		)

	def delete(self, request, album_id: int):
		album = get_object_or_404(Album, pk=album_id, is_approved=True, artist__is_approved=True)
		AlbumLike.objects.filter(user=request.user, album=album).delete()
		likes_count = AlbumLike.objects.filter(album=album).count()
		return Response({"liked": False, "likes_count": likes_count}, status=status.HTTP_200_OK)


class SongLikeView(APIView):
	permission_classes = [IsAuthenticated]

	def _get_song(self, *, song_id: int) -> Song:
		qs = (
		 Song.objects.select_related('artist', 'album')
		 .filter(is_approved=True, artist__is_approved=True)
		 .filter(Q(album__isnull=True) | Q(album__is_approved=True))
		)
		return get_object_or_404(qs, pk=song_id)

	def get(self, request, song_id: int):
		song = self._get_song(song_id=song_id)
		liked = SongLike.objects.filter(user=request.user, song=song).exists()
		likes_count = SongLike.objects.filter(song=song).count()
		return Response({"liked": liked, "likes_count": likes_count}, status=status.HTTP_200_OK)

	def post(self, request, song_id: int):
		song = self._get_song(song_id=song_id)
		_, created = SongLike.objects.get_or_create(user=request.user, song=song)
		likes_count = SongLike.objects.filter(song=song).count()
		return Response(
		 {"liked": True, "created": created, "likes_count": likes_count},
		 status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
		)

	def delete(self, request, song_id: int):
		song = self._get_song(song_id=song_id)
		SongLike.objects.filter(user=request.user, song=song).delete()
		likes_count = SongLike.objects.filter(song=song).count()
		return Response({"liked": False, "likes_count": likes_count}, status=status.HTTP_200_OK)



def _list_prefetches_for_user(*, user):
	album_items_qs = (
	 ListAlbum.objects.select_related('album', 'album__artist')
	 .filter(album__is_approved=True, album__artist__is_approved=True)
	 .order_by('position', 'id')
	 .prefetch_related(
	  Prefetch(
	   'notes',
	   queryset=ListAlbumNote.objects.filter(user=user).order_by('-updated_at', '-id'),
	  ),
	 )
	)
	return [
	 Prefetch('list_albums', queryset=album_items_qs),
	 Prefetch('memberships', queryset=ListMembership.objects.select_related('user').order_by('role', 'id')),
	 'tags',
	]


def _get_list_for_user_or_404(*, user, list_id: int) -> tuple[List, str]:
	qs = (
	 List.objects.select_related('user')
	 .prefetch_related(*_list_prefetches_for_user(user=user))
	 .filter(pk=list_id)
	)
	list_obj = get_object_or_404(qs)
	if list_obj.user_id == user.id:
		return list_obj, ListMembership.Role.OWNER

	role = (
	 ListMembership.objects.filter(list=list_obj, user=user)
	 .values_list('role', flat=True)
	 .first()
	)
	if not role:
		raise Http404
	return list_obj, str(role)


class MyListsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		lists = (
		 List.objects.select_related('user')
		 .filter(Q(user=request.user) | Q(memberships__user=request.user))
		 .distinct()
		 .annotate(albums_count=Count('albums', distinct=True))
		 .prefetch_related(*_list_prefetches_for_user(user=request.user))
		 .order_by('-created_at', '-id')
		)
		output = ListSerializer(lists, many=True, context={'request': request}).data
		return Response(output, status=status.HTTP_200_OK)

	def post(self, request):
		serializer = ListCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		list_obj = List.objects.create(
		 user=request.user,
		 name=serializer.validated_data['name'],
		 description=serializer.validated_data.get('description', ''),
		)
		_create_activity(
		 actor=request.user,
		 activity_type=UserActivity.Type.CREATE_LIST,
		 target_id=list_obj.id,
		 target_name=list_obj.name,
		)
                                                        
		list_obj, _role = _get_list_for_user_or_404(user=request.user, list_id=list_obj.id)
		output = ListSerializer(list_obj, context={'request': request}).data
		return Response(output, status=status.HTTP_201_CREATED)


class ListDetailView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, list_id: int):
		list_obj, _role = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		output = ListSerializer(list_obj, context={'request': request}).data
		return Response(output, status=status.HTTP_200_OK)

	def put(self, request, list_id: int):
		serializer = ListUpdateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		list_obj, role = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		update_fields = []
		if role != ListMembership.Role.OWNER and 'name' in serializer.validated_data:
			return Response(status=status.HTTP_403_FORBIDDEN)
		if 'name' in serializer.validated_data:
			list_obj.name = serializer.validated_data['name']
			update_fields.append('name')
		if 'description' in serializer.validated_data:
			list_obj.description = serializer.validated_data['description']
			update_fields.append('description')
		if not update_fields:
                                         
			list_obj, _role2 = _get_list_for_user_or_404(user=request.user, list_id=list_id)
			output = ListSerializer(list_obj, context={'request': request}).data
			return Response(output, status=status.HTTP_200_OK)
		try:
			list_obj.save(update_fields=[*update_fields, 'updated_at'])
		except IntegrityError:
			return Response(
			 {"detail": "Ai deja o listă cu acest nume."},
			 status=status.HTTP_400_BAD_REQUEST,
			)

		list_obj, _role2 = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		output = ListSerializer(list_obj, context={'request': request}).data
		return Response(output, status=status.HTTP_200_OK)

	def delete(self, request, list_id: int):
		list_obj, role = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		if role != ListMembership.Role.OWNER:
			return Response(status=status.HTTP_403_FORBIDDEN)
		list_obj.delete()
		return Response(status=status.HTTP_204_NO_CONTENT)


class ListAddAlbumView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, list_id: int):
		serializer = ListAlbumAddSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		list_obj, _role = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		album = get_object_or_404(
		 Album,
		 pk=serializer.validated_data['album_id'],
		 is_approved=True,
		 artist__is_approved=True,
		)

		list_album, created = ListAlbum.objects.get_or_create(list=list_obj, album=album)
		if created:
			max_pos = (
			 ListAlbum.objects.filter(list=list_obj)
			 .aggregate(m=Max('position'))
			 .get('m')
			)
			list_album.position = int(max_pos or 0) + 1
			list_album.save(update_fields=['position'])
			_create_activity(
			 actor=request.user,
			 activity_type=UserActivity.Type.LIST_ADD_ALBUM,
			 target_id=album.id,
			 target_name=f"{album.title} (în {list_obj.name})",
			)

		list_obj, _role2 = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		output = ListSerializer(list_obj, context={'request': request}).data
		return Response(
		 output,
		 status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
		)

	def delete(self, request, list_id: int):
		album_id = None
		if isinstance(getattr(request, 'data', None), dict):
			album_id = request.data.get('album_id')
		if album_id in (None, ''):
			album_id = request.query_params.get('album_id')

		try:
			album_id_int = int(str(album_id).strip())
		except Exception:
			return Response({"detail": "album_id is required"}, status=status.HTTP_400_BAD_REQUEST)
		if album_id_int <= 0:
			return Response({"detail": "album_id is required"}, status=status.HTTP_400_BAD_REQUEST)

		list_obj, _role = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		album = get_object_or_404(
		 Album,
		 pk=album_id_int,
		 is_approved=True,
		 artist__is_approved=True,
		)

		ListAlbum.objects.filter(list=list_obj, album=album).delete()

		list_obj, _role2 = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		output = ListSerializer(list_obj, context={'request': request}).data
		return Response(output, status=status.HTTP_200_OK)


class ListReorderAlbumsView(APIView):
	permission_classes = [IsAuthenticated]

	def put(self, request, list_id: int):
		serializer = ListReorderSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		list_obj, _role = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		item_ids = serializer.validated_data.get('item_ids') or []

		existing_ids = list(ListAlbum.objects.filter(list=list_obj).values_list('id', flat=True))
		if len(item_ids) != len(existing_ids):
			return Response(
			 {"detail": "item_ids must include all list items"},
			 status=status.HTTP_400_BAD_REQUEST,
			)
		if set(item_ids) != set(existing_ids):
			return Response(
			 {"detail": "item_ids mismatch"},
			 status=status.HTTP_400_BAD_REQUEST,
			)

		whens = [When(id=item_id, then=Value(idx)) for idx, item_id in enumerate(item_ids, start=1)]
		ListAlbum.objects.filter(list=list_obj, id__in=item_ids).update(
		 position=Case(*whens, default=Value(0), output_field=IntegerField()),
		)

		list_obj, _role2 = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		output = ListSerializer(list_obj, context={'request': request}).data
		return Response(output, status=status.HTTP_200_OK)


class ListCloneView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request, list_id: int):
		source, _role = _get_list_for_user_or_404(user=request.user, list_id=list_id)

		base_name = f"{source.name} (copy)"
		new_name = base_name
		counter = 2
		while List.objects.filter(user=request.user, name=new_name).exists():
			new_name = f"{base_name} {counter}"
			counter += 1

		with transaction.atomic():
			new_list = List.objects.create(
			 user=request.user,
			 name=new_name,
			 description=source.description,
			 is_public=source.is_public,
			)

			source_items = list(source.list_albums.all().order_by('position', 'id'))
			ListAlbum.objects.bulk_create(
			 [
			  ListAlbum(
			   list=new_list,
			   album=item.album,
			   position=int(item.position or 0),
			  )
			  for item in source_items
			 ],
			)

		_create_activity(
		 actor=request.user,
		 activity_type=UserActivity.Type.CREATE_LIST,
		 target_id=new_list.id,
		 target_name=new_list.name,
		)

		new_list, _role2 = _get_list_for_user_or_404(user=request.user, list_id=new_list.id)
		output = ListSerializer(new_list, context={'request': request}).data
		return Response(output, status=status.HTTP_201_CREATED)


class ListCollaboratorsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, list_id: int):
		list_obj, role = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		data = ListSerializer(list_obj, context={'request': request}).data
		return Response(
		 {
		  'my_role': role,
		  'collaborators': data.get('collaborators', []),
		 },
		 status=status.HTTP_200_OK,
		)

	def post(self, request, list_id: int):
		list_obj, role = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		if role != ListMembership.Role.OWNER:
			return Response(status=status.HTTP_403_FORBIDDEN)

		serializer = ListCollaboratorUpsertSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		username = serializer.validated_data['username']
		new_role = serializer.validated_data.get('role') or ListMembership.Role.EDITOR

		User = get_user_model()
		target = get_object_or_404(User, username=username)
		if target.id == list_obj.user_id:
			data = ListSerializer(list_obj, context={'request': request}).data
			return Response({'collaborators': data.get('collaborators', [])}, status=status.HTTP_200_OK)

		ListMembership.objects.update_or_create(
		 list=list_obj,
		 user=target,
		 defaults={'role': new_role},
		)
		list_obj, _role2 = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		data = ListSerializer(list_obj, context={'request': request}).data
		return Response({'collaborators': data.get('collaborators', [])}, status=status.HTTP_200_OK)

	def delete(self, request, list_id: int):
		list_obj, role = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		if role != ListMembership.Role.OWNER:
			return Response(status=status.HTTP_403_FORBIDDEN)

		serializer = ListCollaboratorRemoveSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		user_id = int(serializer.validated_data['user_id'])
		if user_id == list_obj.user_id:
			return Response({"detail": "Cannot remove owner"}, status=status.HTTP_400_BAD_REQUEST)

		ListMembership.objects.filter(list=list_obj, user_id=user_id).delete()
		list_obj, _role2 = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		data = ListSerializer(list_obj, context={'request': request}).data
		return Response({'collaborators': data.get('collaborators', [])}, status=status.HTTP_200_OK)


class ListTagsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, list_id: int):
		list_obj, _role = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		return Response({'tags': [t.name for t in list_obj.tags.all()]}, status=status.HTTP_200_OK)

	def put(self, request, list_id: int):
		list_obj, role = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		if role != ListMembership.Role.OWNER:
			return Response(status=status.HTTP_403_FORBIDDEN)

		serializer = ListTagsUpdateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		names: list[str] = serializer.validated_data.get('tags') or []

		tags = []
		for name in names:
			tag_obj, _ = ListTag.objects.get_or_create(owner=list_obj.user, name=name)
			tags.append(tag_obj)

		list_obj.tags.set(tags)
		list_obj, _role2 = _get_list_for_user_or_404(user=request.user, list_id=list_id)
		data = ListSerializer(list_obj, context={'request': request}).data
		return Response({'tags': data.get('tags', [])}, status=status.HTTP_200_OK)


class ListAlbumNoteView(APIView):
	permission_classes = [IsAuthenticated]

	def put(self, request, item_id: int):
		serializer = ListAlbumNoteUpdateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		item = get_object_or_404(ListAlbum.objects.select_related('list'), pk=item_id)
		_get_list_for_user_or_404(user=request.user, list_id=item.list_id)

		note_obj, _ = ListAlbumNote.objects.update_or_create(
		 list_album=item,
		 user=request.user,
		 defaults={'note': serializer.validated_data.get('note', '')},
		)
		return Response(
		 {'note': note_obj.note, 'updated_at': note_obj.updated_at},
		 status=status.HTTP_200_OK,
		)


class ModerationReportsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		target_type_raw = str(request.query_params.get('target_type', '')).strip().lower()
		target_id_raw = request.query_params.get('target_id', None)
		target_type_filter = target_type_raw if target_type_raw in {'review', 'review_comment', 'song_comment'} else ''
		target_id_filter: int | None = None
		if target_type_filter and target_id_raw not in (None, ''):
			try:
				target_id_filter = int(target_id_raw)
			except (TypeError, ValueError):
				target_id_filter = None
			if target_id_filter is not None and target_id_filter <= 0:
				target_id_filter = None

		status_raw = str(request.query_params.get('status', '')).strip().lower()
		status_filter = status_raw if status_raw in {ModerationReport.Status.PENDING, ModerationReport.Status.RESOLVED} else ''

		reason_code_raw = str(request.query_params.get('reason_code', '')).strip().lower()
		valid_reason_codes = {c for c, _ in ModerationReport.ReasonCode.choices}
		reason_code_filter = reason_code_raw if reason_code_raw in valid_reason_codes else ''

		qs = ModerationReport.objects.select_related('reporter', 'resolved_by')
		if not request.user.is_staff:
			qs = qs.filter(reporter=request.user)
		if target_type_filter and target_id_filter:
			if target_type_filter == 'review':
				qs = qs.filter(review_id=target_id_filter)
			elif target_type_filter == 'review_comment':
				qs = qs.filter(review_comment_id=target_id_filter)
			else:
				qs = qs.filter(song_comment_id=target_id_filter)
		if status_filter:
			qs = qs.filter(status=status_filter)
		if reason_code_filter:
			qs = qs.filter(reason_code=reason_code_filter)

		qs = qs.order_by('-created_at', '-id')[:200]
		return Response(ModerationReportSerializer(qs, many=True).data, status=status.HTTP_200_OK)

	def post(self, request):
		serializer = ModerationReportCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		target_type = serializer.validated_data['target_type']
		target_id = int(serializer.validated_data['target_id'])
		reason_code = serializer.validated_data.get('reason_code') or ModerationReport.ReasonCode.OTHER
		reason = serializer.validated_data.get('reason', '')

		review = None
		review_comment = None
		song_comment = None
		if target_type == 'review':
			review = get_object_or_404(
			 AlbumReview.objects.select_related('album', 'album__artist'),
			 pk=target_id,
			 album__is_approved=True,
			 album__artist__is_approved=True,
			)
		elif target_type == 'review_comment':
			review_comment = get_object_or_404(
			 ReviewComment.objects.select_related('review', 'review__album', 'review__album__artist'),
			 pk=target_id,
			 review__album__is_approved=True,
			 review__album__artist__is_approved=True,
			)
		else:
			song_comment = get_object_or_404(
			 SongComment.objects.select_related('song', 'song__artist', 'song__album'),
			 pk=target_id,
			 song__is_approved=True,
			 song__artist__is_approved=True,
			)

		report_obj, created = ModerationReport.objects.get_or_create(
		 reporter=request.user,
		 review=review,
		 review_comment=review_comment,
		 song_comment=song_comment,
		 status=ModerationReport.Status.PENDING,
		 defaults={'reason': reason, 'reason_code': reason_code},
		)
		if not created:
			changed = False
			if reason and reason != report_obj.reason:
				report_obj.reason = reason
				changed = True
			if reason_code and reason_code != report_obj.reason_code:
				report_obj.reason_code = reason_code
				changed = True
			if changed:
				report_obj.save(update_fields=['reason', 'reason_code'])
		_audit_sensitive_action(
		 actor=request.user,
		 action_type=SensitiveActionAudit.ActionType.REPORT_CREATED,
		 target_type='moderation_report',
		 target_id=report_obj.id,
		 summary='Moderation report created',
		 metadata={'target_type': target_type, 'target_id': target_id, 'reason_code': report_obj.reason_code},
		)

		output = ModerationReportSerializer(report_obj).data
		return Response(output, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ModerationReportResolveView(APIView):
	permission_classes = [IsAuthenticated]

	def put(self, request, report_id: int):
		if not request.user.is_staff:
			return Response(status=status.HTTP_403_FORBIDDEN)

		report_obj = get_object_or_404(ModerationReport, pk=report_id)
		if report_obj.status != ModerationReport.Status.RESOLVED:
			resolution_reason = str(request.data.get('resolution_reason', '') or '').strip()
			resolution_feedback = str(request.data.get('resolution_feedback', '') or '').strip()
			if not resolution_reason:
				if report_obj.reason_code:
					resolution_reason = report_obj.get_reason_code_display()
				else:
					resolution_reason = 'Raport verificat'
			if not resolution_feedback:
				if report_obj.reason:
					resolution_feedback = report_obj.reason
				else:
					resolution_feedback = 'Raportul a fost verificat și închis de echipa de moderare.'
			report_obj.status = ModerationReport.Status.RESOLVED
			report_obj.resolved_by = request.user
			report_obj.resolved_at = timezone.now()
			report_obj.resolution_reason = resolution_reason
			report_obj.resolution_feedback = resolution_feedback
			report_obj.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_reason', 'resolution_feedback'])
			_audit_sensitive_action(
			 actor=request.user,
			 action_type=SensitiveActionAudit.ActionType.REPORT_RESOLVED,
			 target_type='moderation_report',
			 target_id=report_obj.id,
			 summary='Moderation report resolved',
			 metadata={
			  'report_target_type': 'review' if report_obj.review_id else 'review_comment' if report_obj.review_comment_id else 'song_comment',
			  'report_target_id': int(report_obj.review_id or report_obj.review_comment_id or report_obj.song_comment_id),
			  'resolution_reason': resolution_reason,
			 },
			)
		return Response(ModerationReportSerializer(report_obj).data, status=status.HTTP_200_OK)


def _generate_unique_song_slug(*, base: str) -> str:
	base_slug = slugify(str(base or ''))
	if not base_slug:
		base_slug = 'song'
	slug = base_slug
	suffix = 2
	while Song.objects.filter(slug=slug).exists():
		slug = f"{base_slug}-{suffix}"
		suffix += 1
	return slug


def _apply_metadata_suggestion(*, suggestion: MetadataSuggestion) -> bool:
\
\
\
\
    
	kind = suggestion.kind
	payload = suggestion.payload or {}

	if kind == MetadataSuggestion.Kind.RELEASE_DATE:
		if not suggestion.album_id:
			raise ValueError('release_date suggestions must target an album')
		before = getattr(suggestion.album, 'release_date', None)
		release_date = payload.get('release_date')
		if not release_date:
			raise ValueError('payload.release_date is required')
		suggestion.album.release_date = release_date
		suggestion.album.save(update_fields=['release_date'])
		CatalogChangelogEvent.objects.create(
		 actor=suggestion.reviewed_by,
		 suggestion=suggestion,
		 album=suggestion.album,
		 kind=kind,
		 summary='Data de lansare actualizată',
		 diff={'field': 'release_date', 'before': str(before) if before else None, 'after': str(release_date)},
		)
		return True

	if kind == MetadataSuggestion.Kind.COVER_URL:
		if not suggestion.album_id:
			raise ValueError('cover_url suggestions must target an album')
		before = str(getattr(suggestion.album, 'cover_url', '') or '')
		cover_url = str(payload.get('cover_url', '') or '').strip()
		if not cover_url:
			raise ValueError('payload.cover_url is required')
		suggestion.album.cover_url = cover_url
		suggestion.album.save(update_fields=['cover_url'])
		CatalogChangelogEvent.objects.create(
		 actor=suggestion.reviewed_by,
		 suggestion=suggestion,
		 album=suggestion.album,
		 kind=kind,
		 summary='Coperta actualizată',
		 diff={'field': 'cover_url', 'before': before or None, 'after': cover_url},
		)
		return True

	if kind == MetadataSuggestion.Kind.IMAGE_URL:
		if not suggestion.artist_id:
			raise ValueError('image_url suggestions must target an artist')
		before = str(getattr(suggestion.artist, 'image_url', '') or '')
		image_url = str(payload.get('image_url', '') or '').strip()
		if not image_url:
			raise ValueError('payload.image_url is required')
		suggestion.artist.image_url = image_url
		suggestion.artist.save(update_fields=['image_url'])
		CatalogChangelogEvent.objects.create(
		 actor=suggestion.reviewed_by,
		 suggestion=suggestion,
		 artist=suggestion.artist,
		 kind=kind,
		 summary='Imagine artist actualizată',
		 diff={'field': 'image_url', 'before': before or None, 'after': image_url},
		)
		return True

	if kind == MetadataSuggestion.Kind.BIO:
		if not suggestion.artist_id:
			raise ValueError('bio suggestions must target an artist')
		before = str(getattr(suggestion.artist, 'bio', '') or '')
		bio = str(payload.get('bio', '') or '').strip()
		if not bio:
			raise ValueError('payload.bio is required')
		suggestion.artist.bio = bio
		suggestion.artist.save(update_fields=['bio'])
		CatalogChangelogEvent.objects.create(
		 actor=suggestion.reviewed_by,
		 suggestion=suggestion,
		 artist=suggestion.artist,
		 kind=kind,
		 summary='Biografie actualizată',
		 diff={'field': 'bio', 'before': before or None, 'after': bio},
		)
		return True

	if kind == MetadataSuggestion.Kind.ALIASES:
		if not suggestion.artist_id:
			raise ValueError('aliases suggestions must target an artist')
		before = str(getattr(suggestion.artist, 'aliases', '') or '')
		aliases = str(payload.get('aliases', '') or '').strip()
		if not aliases:
			raise ValueError('payload.aliases is required')
		suggestion.artist.aliases = aliases
		suggestion.artist.save(update_fields=['aliases'])
		CatalogChangelogEvent.objects.create(
		 actor=suggestion.reviewed_by,
		 suggestion=suggestion,
		 artist=suggestion.artist,
		 kind=kind,
		 summary='Alias-uri actualizate',
		 diff={'field': 'aliases', 'before': before or None, 'after': aliases},
		)
		return True

	if kind == MetadataSuggestion.Kind.DESCRIPTION:
		description = str(payload.get('description', '') or '').strip()
		if not description:
			raise ValueError('payload.description is required')
		if suggestion.album_id:
			before = str(getattr(suggestion.album, 'description', '') or '')
			suggestion.album.description = description
			suggestion.album.save(update_fields=['description'])
			CatalogChangelogEvent.objects.create(
			 actor=suggestion.reviewed_by,
			 suggestion=suggestion,
			 album=suggestion.album,
			 kind=kind,
			 summary='Descriere actualizată',
			 diff={'field': 'description', 'before': before or None, 'after': description},
			)
			return True
		if suggestion.song_id:
			before = str(getattr(suggestion.song, 'description', '') or '')
			suggestion.song.description = description
			suggestion.song.save(update_fields=['description'])
                                                                      
			return True
		raise ValueError('description suggestions must target an album or song')

	if kind == MetadataSuggestion.Kind.TRACKLIST:
		if not suggestion.album_id:
			raise ValueError('tracklist suggestions must target an album')
		tracks = payload.get('tracks')
		if not isinstance(tracks, list) or not tracks:
			raise ValueError('payload.tracks must be a non-empty list')
		album = suggestion.album
		artist = album.artist
		created_count = 0
		updated_count = 0
		for t in tracks:
			if not isinstance(t, dict):
				continue
			title = str(t.get('title', '') or '').strip()
			track_number = t.get('track_number', None)
			if not title or track_number is None:
				continue
			try:
				track_number_int = int(track_number)
			except (TypeError, ValueError):
				continue
			duration = t.get('duration_seconds', None)
			duration_int = 0
			if duration not in (None, ''):
				try:
					duration_int = max(0, int(duration))
				except (TypeError, ValueError):
					duration_int = 0
			song = Song.objects.filter(album=album, track_number=track_number_int).first()
			if song:
				updates = []
				if song.title != title:
					song.title = title
					updates.append('title')
				if duration is not None and song.duration_seconds != duration_int:
					song.duration_seconds = duration_int
					updates.append('duration_seconds')
				if not song.is_approved:
					song.is_approved = True
					updates.append('is_approved')
				if updates:
					song.save(update_fields=updates)
					updated_count += 1
				continue

			slug = _generate_unique_song_slug(base=title)
			Song.objects.create(
			 album=album,
			 artist=artist,
			 title=title,
			 slug=slug,
			 track_number=track_number_int,
			 duration_seconds=duration_int,
			 is_approved=True,
			)
			created_count += 1
		CatalogChangelogEvent.objects.create(
		 actor=suggestion.reviewed_by,
		 suggestion=suggestion,
		 album=album,
		 kind=kind,
		 summary='Tracklist actualizat',
		 diff={'created': created_count, 'updated': updated_count},
		)
		return True

                                     
	return False


class MetadataSuggestionsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		status_raw = str(request.query_params.get('status', '')).strip().lower()
		valid_status = {c for c, _ in MetadataSuggestion.Status.choices}
		status_filter = status_raw if status_raw in valid_status else ''

		kind_raw = str(request.query_params.get('kind', '')).strip().lower()
		valid_kind = {c for c, _ in MetadataSuggestion.Kind.choices}
		kind_filter = kind_raw if kind_raw in valid_kind else ''

		qs = MetadataSuggestion.objects.select_related('suggester', 'reviewed_by', 'artist', 'album', 'song')
		if not request.user.is_staff:
			qs = qs.filter(suggester=request.user)
		if status_filter:
			qs = qs.filter(status=status_filter)
		if kind_filter:
			qs = qs.filter(kind=kind_filter)

		qs = qs.order_by('-created_at', '-id')[:200]
		return Response(MetadataSuggestionSerializer(qs, many=True).data, status=status.HTTP_200_OK)

	def post(self, request):
		serializer = MetadataSuggestionCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		target_type = serializer.validated_data['target_type']
		target_id = int(serializer.validated_data['target_id'])
		kind = serializer.validated_data['kind']
		payload = serializer.validated_data.get('payload') or {}
		note = serializer.validated_data.get('note', '')

		artist = None
		album = None
		song = None
		if target_type == 'artist':
			artist = get_object_or_404(Artist, pk=target_id, is_approved=True)
		elif target_type == 'album':
			album = get_object_or_404(Album.objects.select_related('artist'), pk=target_id, is_approved=True, artist__is_approved=True)
		else:
			song = get_object_or_404(
			 Song.objects.select_related('artist', 'album', 'album__artist')
			 .filter(is_approved=True, artist__is_approved=True)
			 .filter(Q(album__isnull=True) | Q(album__is_approved=True, album__artist__is_approved=True)),
			 pk=target_id,
			)

		suggestion = MetadataSuggestion.objects.create(
		 suggester=request.user,
		 artist=artist,
		 album=album,
		 song=song,
		 kind=kind,
		 payload=payload,
		 note=note,
		)
		_audit_sensitive_action(
		 actor=request.user,
		 action_type=SensitiveActionAudit.ActionType.METADATA_SUGGESTION_CREATED,
		 target_type='metadata_suggestion',
		 target_id=suggestion.id,
		 summary='Metadata suggestion created',
		 metadata={'target_type': target_type, 'target_id': target_id, 'kind': kind},
		)
		return Response(MetadataSuggestionSerializer(suggestion).data, status=status.HTTP_201_CREATED)


class MetadataSuggestionDecisionView(APIView):
	permission_classes = [IsAuthenticated]

	def put(self, request, suggestion_id: int):
		if not request.user.is_staff:
			return Response(status=status.HTTP_403_FORBIDDEN)

		action = str(request.data.get('action', '')).strip().lower()
		if action not in {'approve', 'reject'}:
			return Response({'action': 'action must be approve|reject'}, status=status.HTTP_400_BAD_REQUEST)
		decision_note = str(request.data.get('decision_note', '') or '')
		apply = request.data.get('apply', True)
		apply = bool(apply)

		suggestion = get_object_or_404(
		 MetadataSuggestion.objects.select_related('artist', 'album', 'album__artist', 'song', 'song__artist', 'song__album', 'suggester'),
		 pk=suggestion_id,
		)
		if suggestion.status != MetadataSuggestion.Status.PENDING:
			return Response(MetadataSuggestionSerializer(suggestion).data, status=status.HTTP_200_OK)

		with transaction.atomic():
			if action == 'reject':
				suggestion.status = MetadataSuggestion.Status.REJECTED
				suggestion.reviewed_by = request.user
				suggestion.reviewed_at = timezone.now()
				suggestion.decision_note = decision_note
				suggestion.applied = False
				suggestion.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'decision_note', 'applied'])
				_audit_sensitive_action(
				 actor=request.user,
				 action_type=SensitiveActionAudit.ActionType.METADATA_SUGGESTION_DECIDED,
				 target_type='metadata_suggestion',
				 target_id=suggestion.id,
				 summary='Metadata suggestion rejected',
				 metadata={'decision': 'reject', 'kind': suggestion.kind, 'applied': False},
				)
				return Response(MetadataSuggestionSerializer(suggestion).data, status=status.HTTP_200_OK)

			applied = False
			if apply:
				try:
					applied = bool(_apply_metadata_suggestion(suggestion=suggestion))
				except ValueError as e:
					return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

			suggestion.status = MetadataSuggestion.Status.APPROVED
			suggestion.reviewed_by = request.user
			suggestion.reviewed_at = timezone.now()
			suggestion.decision_note = decision_note
			suggestion.applied = bool(applied)
			suggestion.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'decision_note', 'applied'])
			_audit_sensitive_action(
			 actor=request.user,
			 action_type=SensitiveActionAudit.ActionType.METADATA_SUGGESTION_DECIDED,
			 target_type='metadata_suggestion',
			 target_id=suggestion.id,
			 summary='Metadata suggestion approved',
			 metadata={'decision': 'approve', 'kind': suggestion.kind, 'applied': bool(applied)},
			)
			return Response(MetadataSuggestionSerializer(suggestion).data, status=status.HTTP_200_OK)


class AlbumReviewHistoryView(APIView):
	permission_classes = [AllowAny]

	def get(self, request, review_id: int):
		review = get_object_or_404(
		 AlbumReview.objects.select_related('album', 'album__artist'),
		 pk=review_id,
		 album__is_approved=True,
		 album__artist__is_approved=True,
		)
		edits = AlbumReviewEdit.objects.select_related('edited_by').filter(review=review).order_by('-edited_at', '-id')[:50]
		return Response(AlbumReviewEditSerializer(edits, many=True).data, status=status.HTTP_200_OK)


class AlbumReviewDraftView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, album_id: int):
		album = get_object_or_404(Album, pk=album_id, is_approved=True, artist__is_approved=True)
		draft = AlbumReviewDraft.objects.filter(user=request.user, album=album).first()
		if not draft:
			return Response({'title': '', 'content': '', 'updated_at': None}, status=status.HTTP_200_OK)
		return Response(AlbumReviewDraftSerializer(draft).data, status=status.HTTP_200_OK)

	def put(self, request, album_id: int):
		serializer = AlbumReviewDraftUpsertSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		album = get_object_or_404(Album, pk=album_id, is_approved=True, artist__is_approved=True)
		draft, _ = AlbumReviewDraft.objects.update_or_create(
		 user=request.user,
		 album=album,
		 defaults={
		  'title': serializer.validated_data.get('title', ''),
		  'content': serializer.validated_data.get('content', ''),
		 },
		)
		return Response(AlbumReviewDraftSerializer(draft).data, status=status.HTTP_200_OK)

	def delete(self, request, album_id: int):
		album = get_object_or_404(Album, pk=album_id, is_approved=True, artist__is_approved=True)
		AlbumReviewDraft.objects.filter(user=request.user, album=album).delete()
		return Response(status=status.HTTP_204_NO_CONTENT)


class MyTopStatsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
                                           
		today = timezone.localdate()
		period_raw = str(request.query_params.get('period', 'month') or '').strip().lower()
		period = period_raw if period_raw in {'month', 'year', 'all'} else 'month'

		limit_raw = str(request.query_params.get('limit', '')).strip()
		limit = 10
		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 10
		limit = max(1, min(limit, 50))

		year = today.year
		month = today.month
		if period in {'month', 'year'}:
			year_raw = str(request.query_params.get('year', '')).strip()
			if year_raw:
				try:
					year = int(year_raw)
				except ValueError:
					return Response({"detail": "Invalid year"}, status=status.HTTP_400_BAD_REQUEST)
			if year < 1900 or year > 2100:
				return Response({"detail": "Invalid year"}, status=status.HTTP_400_BAD_REQUEST)

			if period == 'month':
				month_raw = str(request.query_params.get('month', '')).strip()
				if month_raw:
					try:
						month = int(month_raw)
					except ValueError:
						return Response({"detail": "Invalid month"}, status=status.HTTP_400_BAD_REQUEST)
				if month < 1 or month > 12:
					return Response({"detail": "Invalid month"}, status=status.HTTP_400_BAD_REQUEST)

		start_date: date | None = None
		end_date: date | None = None
		previous_start_date: date | None = None
		previous_end_date: date | None = None
		if period == 'year':
			start_date = date(year, 1, 1)
			end_date = date(year, 12, 31)
			previous_start_date = date(year - 1, 1, 1)
			previous_end_date = date(year - 1, 12, 31)
		elif period == 'month':
			last_day = monthrange(year, month)[1]
			start_date = date(year, month, 1)
			end_date = date(year, month, last_day)
			if month == 1:
				previous_year = year - 1
				previous_month = 12
			else:
				previous_year = year
				previous_month = month - 1
			previous_last_day = monthrange(previous_year, previous_month)[1]
			previous_start_date = date(previous_year, previous_month, 1)
			previous_end_date = date(previous_year, previous_month, previous_last_day)

		def _with_optional_period(qs, *, from_date: date | None, to_date: date | None, field_name: str):
			if from_date is not None and to_date is not None:
				kwargs = {
				 f"{field_name}__gte": from_date,
				 f"{field_name}__lte": to_date,
				}
				return qs.filter(**kwargs)
			return qs

		def _compute_totals(listens_queryset):
			album_counts_local = list(
			 listens_queryset.values('album_id').annotate(c=Count('id')).order_by('-c')
			)
			album_ids_local = [int(r['album_id']) for r in album_counts_local if r.get('album_id')]
			durations_by_album_local: dict[int, int] = {}
			if album_ids_local:
				duration_rows_local = (
				 Song.objects.filter(
				  album_id__in=album_ids_local,
				  is_approved=True,
				  artist__is_approved=True,
				 )
				 .values('album_id')
				 .annotate(d=Sum('duration_seconds'))
				)
				durations_by_album_local = {
				 int(r['album_id']): int(r['d'] or 0)
				 for r in duration_rows_local
				 if r.get('album_id')
				}

			total_seconds_local = int(
			 sum(
			  int(r.get('c') or 0) * int(durations_by_album_local.get(int(r['album_id']), 0))
			  for r in album_counts_local
			 )
			)

			return {
			 "listen_events": int(listens_queryset.count()),
			 "listen_days": int(listens_queryset.values('listened_date').distinct().count()),
			 "distinct_albums": int(listens_queryset.values('album_id').distinct().count()),
			 "total_listen_seconds": int(total_seconds_local),
			}

		listens_qs = AlbumListen.objects.filter(
		 user=request.user,
		 album__is_approved=True,
		 album__artist__is_approved=True,
		)
		listens_qs = _with_optional_period(
		 listens_qs,
		 from_date=start_date,
		 to_date=end_date,
		 field_name='listened_date',
		)

		base_listens_qs = AlbumListen.objects.filter(
		 user=request.user,
		 album__is_approved=True,
		 album__artist__is_approved=True,
		)
		previous_listens_qs = _with_optional_period(
		 base_listens_qs,
		 from_date=previous_start_date,
		 to_date=previous_end_date,
		 field_name='listened_date',
		)

		totals = _compute_totals(listens_qs)
		previous_totals = _compute_totals(previous_listens_qs)

		album_counts = list(listens_qs.values('album_id').annotate(c=Count('id')).order_by('-c'))
		album_ids = [int(r['album_id']) for r in album_counts if r.get('album_id')]
		durations_by_album: dict[int, int] = {}
		if album_ids:
			duration_rows = (
			 Song.objects.filter(
			  album_id__in=album_ids,
			  is_approved=True,
			  artist__is_approved=True,
			 )
			 .values('album_id')
			 .annotate(d=Sum('duration_seconds'))
			)
			durations_by_album = {
			 int(r['album_id']): int(r['d'] or 0)
			 for r in duration_rows
			 if r.get('album_id')
			}

		top_albums_rows = (
		 listens_qs.values(
		  'album_id',
		  'album__title',
		  'album__slug',
		  'album__artist__id',
		  'album__artist__name',
		  'album__artist__slug',
		 )
		 .annotate(listens=Count('id'))
		 .order_by('-listens', 'album__title', 'album_id')
		)[:limit]
		top_albums = [
		 {
		  "album_id": int(r['album_id']),
		  "album_title": r['album__title'],
		  "album_slug": r['album__slug'],
		  "artist_id": int(r['album__artist__id']),
		  "artist_name": r['album__artist__name'],
		  "artist_slug": r['album__artist__slug'],
		  "listens": int(r['listens'] or 0),
		  "album_duration_seconds": int(durations_by_album.get(int(r['album_id']), 0)),
		 }
		 for r in top_albums_rows
		]

		top_artists_rows = (
		 listens_qs.values(
		  'album__artist__id',
		  'album__artist__name',
		  'album__artist__slug',
		 )
		 .annotate(listens=Count('id'))
		 .order_by('-listens', 'album__artist__name', 'album__artist__id')
		)[:limit]
		top_artists = [
		 {
		  "artist_id": int(r['album__artist__id']),
		  "artist_name": r['album__artist__name'],
		  "artist_slug": r['album__artist__slug'],
		  "listens": int(r['listens'] or 0),
		 }
		 for r in top_artists_rows
		]

		top_genres_rows = (
		 listens_qs.values(
		  'album__genres__id',
		  'album__genres__name',
		  'album__genres__slug',
		 )
		 .exclude(album__genres__id__isnull=True)
		 .annotate(listens=Count('id'))
		 .order_by('-listens', 'album__genres__name', 'album__genres__id')
		)[:limit]
		top_genres = [
		 {
		  "genre_id": int(r['album__genres__id']),
		  "genre_name": r['album__genres__name'],
		  "genre_slug": r['album__genres__slug'],
		  "listens": int(r['listens'] or 0),
		 }
		 for r in top_genres_rows
		]

		song_ratings_qs = SongRating.objects.select_related('song', 'song__artist').filter(
		 user=request.user,
		 song__is_approved=True,
		 song__artist__is_approved=True,
		)
		if start_date is not None and end_date is not None:
			song_ratings_qs = song_ratings_qs.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

		top_songs_items = list(song_ratings_qs.order_by('-rating', '-created_at', '-id')[:limit])
		top_songs = [
		 {
		  "song_id": int(sr.song_id),
		  "song_title": sr.song.title,
		  "song_slug": sr.song.slug,
		  "artist_id": int(sr.song.artist_id),
		  "artist_name": sr.song.artist.name,
		  "artist_slug": sr.song.artist.slug,
		  "rating": int(sr.rating),
		  "created_at": sr.created_at,
		 }
		 for sr in top_songs_items
		]

                                 
		all_days = list(
		 AlbumListen.objects.filter(
		  user=request.user,
		  album__is_approved=True,
		  album__artist__is_approved=True,
		 )
		 .values_list('listened_date', flat=True)
		 .distinct()
		)
		day_set = set(all_days)
		last_listen_date = max(day_set) if day_set else None
		current_streak_days = 0
		if last_listen_date is not None:
			d = last_listen_date
			while d in day_set:
				current_streak_days += 1
				d = d - timedelta(days=1)

		best_streak_days = 0
		if day_set:
			sorted_days = sorted(day_set)
			best = 1
			cur = 1
			for idx in range(1, len(sorted_days)):
				if sorted_days[idx] == sorted_days[idx - 1] + timedelta(days=1):
					cur += 1
				else:
					best = max(best, cur)
					cur = 1
			best = max(best, cur)
			best_streak_days = int(best)

		def _build_delta(current_value: int, previous_value: int):
			delta_value = int(current_value) - int(previous_value)
			if int(previous_value) == 0:
				pct_change = None if int(current_value) == 0 else 100.0
			else:
				pct_change = round((delta_value / float(previous_value)) * 100.0, 2)
			return {
			 "current": int(current_value),
			 "previous": int(previous_value),
			 "delta": int(delta_value),
			 "pct_change": pct_change,
			}

		comparison = {
		 "available": bool(period in {'month', 'year'}),
		 "period": {
		  "start_date": previous_start_date,
		  "end_date": previous_end_date,
		 },
		 "totals": {
		  "listen_events": _build_delta(totals['listen_events'], previous_totals['listen_events']),
		  "listen_days": _build_delta(totals['listen_days'], previous_totals['listen_days']),
		  "distinct_albums": _build_delta(totals['distinct_albums'], previous_totals['distinct_albums']),
		  "total_listen_seconds": _build_delta(totals['total_listen_seconds'], previous_totals['total_listen_seconds']),
		 },
		}

		payload = {
		 "period": {
		  "type": period,
		  "year": int(year) if period in {'month', 'year'} else None,
		  "month": int(month) if period == 'month' else None,
		  "start_date": start_date,
		  "end_date": end_date,
		 },
		 "totals": totals,
		 "streak": {
		  "current_days": int(current_streak_days),
		  "best_days": int(best_streak_days),
		  "last_listen_date": last_listen_date,
		 },
		 "top_artists": top_artists,
		 "top_albums": top_albums,
		 "top_genres": top_genres,
		 "top_songs": top_songs,
		 "top_songs_source": "song_ratings",
		 "comparison": comparison,
		}
		return Response(payload, status=status.HTTP_200_OK)


class ArtistFollowView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, artist_id: int):
		artist = get_object_or_404(Artist, pk=artist_id, is_approved=True)
		is_following = ArtistFollow.objects.filter(user=request.user, artist=artist).exists()
		return Response(FollowStatusSerializer({"is_following": is_following}).data, status=status.HTTP_200_OK)

	def post(self, request, artist_id: int):
		artist = get_object_or_404(Artist, pk=artist_id, is_approved=True)
		_, created = ArtistFollow.objects.get_or_create(user=request.user, artist=artist)
		if created:
			_create_activity(
			 actor=request.user,
			 activity_type=UserActivity.Type.FOLLOW_ARTIST,
			 target_id=artist.id,
			 target_name=artist.name,
			)
			_track_analytics_event(
			 user=request.user,
			 event_name='follow_artist',
			 target_type='artist',
			 target_id=artist.id,
			 properties={'artist_slug': artist.slug},
			)
			invalidate_user_recommendations(request.user.id)
		return Response(
		 FollowStatusSerializer({"is_following": True}).data,
		 status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
		)

	def delete(self, request, artist_id: int):
		artist = get_object_or_404(Artist, pk=artist_id, is_approved=True)
		ArtistFollow.objects.filter(user=request.user, artist=artist).delete()
		return Response(FollowStatusSerializer({"is_following": False}).data, status=status.HTTP_200_OK)


class FollowedArtistsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		follows = (
		 ArtistFollow.objects.select_related('artist')
		 .filter(user=request.user, artist__is_approved=True)
		 .order_by('-created_at')
		)
		return Response(FollowedArtistSerializer(follows, many=True).data, status=status.HTTP_200_OK)


class MyReviewsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		reviews = (
		 AlbumReview.objects.select_related('user', 'album', 'album__artist')
		 .filter(
		  user=request.user,
		  album__is_approved=True,
		  album__artist__is_approved=True,
		 )
		 .annotate(likes_count=Count('likes'))
		 .order_by('-created_at')
		)
		output = MyAlbumReviewSerializer(reviews, many=True).data
		return Response(output, status=status.HTTP_200_OK)


class MyRatingsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		album_ratings = (
		 AlbumRating.objects.select_related('user', 'album', 'album__artist')
		 .filter(
		  user=request.user,
		  album__is_approved=True,
		  album__artist__is_approved=True,
		 )
		 .order_by('-created_at', '-id')
		)

		song_ratings = (
		 SongRating.objects.select_related('user', 'song', 'song__artist', 'song__album', 'song__album__artist')
		 .filter(
		  user=request.user,
		  song__is_approved=True,
		  song__artist__is_approved=True,
		 )
		 .filter(
		  Q(song__album__isnull=True)
		  | Q(song__album__is_approved=True, song__album__artist__is_approved=True)
		 )
		 .order_by('-created_at', '-id')
		)

		album_paginator = AlbumRatingsPagination()
		album_page = album_paginator.paginate_queryset(album_ratings, request, view=self)
		if album_page is None:
			album_payload = {
			 'count': album_ratings.count(),
			 'next': None,
			 'previous': None,
			 'results': MyAlbumRatingSerializer(album_ratings, many=True).data,
			}
		else:
			album_payload = album_paginator.get_paginated_response(
			 MyAlbumRatingSerializer(album_page, many=True).data,
			).data

		song_paginator = SongRatingsPagination()
		song_page = song_paginator.paginate_queryset(song_ratings, request, view=self)
		if song_page is None:
			song_payload = {
			 'count': song_ratings.count(),
			 'next': None,
			 'previous': None,
			 'results': MySongRatingSerializer(song_ratings, many=True).data,
			}
		else:
			song_payload = song_paginator.get_paginated_response(
			 MySongRatingSerializer(song_page, many=True).data,
			).data

		payload = {
		 "albums": album_payload,
		 "songs": song_payload,
		}
		return Response(payload, status=status.HTTP_200_OK)


class MyLikedAlbumsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		qs = (
		 AlbumLike.objects.select_related('album', 'album__artist')
		 .filter(
		  user=request.user,
		  album__is_approved=True,
		  album__artist__is_approved=True,
		 )
		 .order_by('-created_at', '-id')
		)
		paginator = WantToListenPagination()
		page = paginator.paginate_queryset(qs, request, view=self)
		if page is None:
			return Response(MyAlbumLikeSerializer(qs, many=True).data, status=status.HTTP_200_OK)
		serializer = MyAlbumLikeSerializer(page, many=True)
		return paginator.get_paginated_response(serializer.data)


class MyListensView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		limit_raw = str(request.query_params.get('limit', '')).strip()
		limit = 50
		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 50
		limit = max(1, min(limit, 200))

		qs = (
		 AlbumListen.objects.select_related('album', 'album__artist')
		 .filter(
		  user=request.user,
		  album__is_approved=True,
		  album__artist__is_approved=True,
		 )
		)
		qs = _with_album_listen_album_filter(qs).order_by('-listened_at', '-id')[:limit]

		return Response(MyAlbumListenSerializer(qs, many=True).data, status=status.HTTP_200_OK)


class MyWantToListenView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		qs = (
		 WantToListen.objects.select_related('album', 'album__artist')
		 .filter(
		  user=request.user,
		  album__is_approved=True,
		  album__artist__is_approved=True,
		 )
		 .order_by('-created_at', '-id')
		)
		paginator = WantToListenPagination()
		page = paginator.paginate_queryset(qs, request, view=self)
		if page is None:
			return Response(MyWantToListenSerializer(qs, many=True).data, status=status.HTTP_200_OK)
		serializer = MyWantToListenSerializer(page, many=True)
		return paginator.get_paginated_response(serializer.data)


class MyListensStatsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		today = timezone.localdate()
		base_qs = AlbumListen.objects.filter(
		 user=request.user,
		 album__is_approved=True,
		 album__artist__is_approved=True,
		)
		base_qs = _with_album_listen_album_filter(base_qs)
		total_albums = base_qs.values('album_id').distinct().count()
		year_albums = (
		 base_qs.filter(listened_date__year=today.year)
		 .values('album_id')
		 .distinct()
		 .count()
		)

		payload = {
		 "total_albums": int(total_albums),
		 "year_albums": int(year_albums),
		 "year": int(today.year),
		}
		return Response(payload, status=status.HTTP_200_OK)


class MyStatsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		payload = profile_stats_payload_for(request.user)
		return Response(ProfileStatsSerializer(payload).data, status=status.HTTP_200_OK)


class MyStreakView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		payload = streak_payload_for(request.user)
		return Response(payload, status=status.HTTP_200_OK)


class WeeklyChallengesView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		payload = weekly_challenges_payload_for(request.user)
		return Response(payload, status=status.HTTP_200_OK)


class MyPrivacySettingsView(APIView):
	permission_classes = [IsAuthenticated]
	throttle_classes = [ScopedRateThrottle]
	throttle_scope = 'profile_update'

	def get(self, request):
		settings_obj, _ = UserPrivacySettings.objects.get_or_create(user=request.user)
		return Response(UserPrivacySettingsSerializer(settings_obj).data, status=status.HTTP_200_OK)

	def put(self, request):
		settings_obj, _ = UserPrivacySettings.objects.get_or_create(user=request.user)
		serializer = UserPrivacySettingsSerializer(settings_obj, data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(serializer.data, status=status.HTTP_200_OK)


class MyDataExportView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		fmt = str(request.query_params.get('format', '') or '').strip().lower() or 'json'
		resource = str(request.query_params.get('resource', '') or '').strip().lower()
		limit_raw = str(request.query_params.get('limit', '')).strip()
		limit = 5000
		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 5000
		limit = max(1, min(limit, 10000))

		listens_qs = (
		 AlbumListen.objects.select_related('album', 'album__artist')
		 .filter(user=request.user, album__is_approved=True, album__artist__is_approved=True)
		)
		listens_qs = _with_album_listen_album_filter(listens_qs).order_by('-listened_at', '-id')
		ratings_qs = (
		 AlbumRating.objects.select_related('album', 'album__artist')
		 .filter(user=request.user, album__is_approved=True, album__artist__is_approved=True)
		 .order_by('-created_at', '-id')
		)
		reviews_qs = (
		 AlbumReview.objects.select_related('album', 'album__artist')
		 .filter(user=request.user, album__is_approved=True, album__artist__is_approved=True)
		 .order_by('-created_at', '-id')
		)
		activity_qs = (
		 UserActivity.objects.select_related('actor')
		 .filter(actor=request.user)
		 .order_by('-created_at', '-id')
		)
		lists_qs = (
		 List.objects.filter(user=request.user)
		 .annotate(albums_count=Count('albums', distinct=True))
		 .order_by('-created_at', '-id')
		)

		if fmt == 'csv':
			if resource not in {'listens', 'ratings', 'reviews', 'activity', 'lists'}:
				return Response(
				 {"detail": "resource must be one of: listens, ratings, reviews, activity, lists"},
				 status=status.HTTP_400_BAD_REQUEST,
				)
			filename = f"export_{resource}_{request.user.username}.csv"
			buffer = io.StringIO()
			writer = csv.writer(buffer)

			if resource == 'listens':
				writer.writerow([
				 "listened_at",
				 "listened_date",
				 "album_id",
				 "album_title",
				 "album_slug",
				 "artist_name",
				 "artist_slug",
				])
				for it in listens_qs[:limit]:
					writer.writerow([
					 it.listened_at.isoformat() if it.listened_at else "",
					 it.listened_date.isoformat() if it.listened_date else "",
					 it.album_id,
					 getattr(it.album, 'title', ''),
					 getattr(it.album, 'slug', ''),
					 getattr(getattr(it.album, 'artist', None), 'name', ''),
					 getattr(getattr(it.album, 'artist', None), 'slug', ''),
					])

			elif resource == 'ratings':
				writer.writerow([
				 "created_at",
				 "rating",
				 "album_id",
				 "album_title",
				 "album_slug",
				 "artist_name",
				 "artist_slug",
				])
				for it in ratings_qs[:limit]:
					writer.writerow([
					 it.created_at.isoformat() if it.created_at else "",
					 int(it.rating) if it.rating is not None else "",
					 it.album_id,
					 getattr(it.album, 'title', ''),
					 getattr(it.album, 'slug', ''),
					 getattr(getattr(it.album, 'artist', None), 'name', ''),
					 getattr(getattr(it.album, 'artist', None), 'slug', ''),
					])

			elif resource == 'reviews':
				writer.writerow([
				 "created_at",
				 "updated_at",
				 "title",
				 "content",
				 "album_id",
				 "album_title",
				 "album_slug",
				 "artist_name",
				 "artist_slug",
				])
				for it in reviews_qs[:limit]:
					writer.writerow([
					 it.created_at.isoformat() if it.created_at else "",
					 it.updated_at.isoformat() if it.updated_at else "",
					 it.title or "",
					 it.content or "",
					 it.album_id,
					 getattr(it.album, 'title', ''),
					 getattr(it.album, 'slug', ''),
					 getattr(getattr(it.album, 'artist', None), 'name', ''),
					 getattr(getattr(it.album, 'artist', None), 'slug', ''),
					])

			elif resource == 'activity':
				writer.writerow([
				 "created_at",
				 "activity_type",
				 "target_id",
				 "target_name",
				 "rating",
				])
				for it in activity_qs[:limit]:
					writer.writerow([
					 it.created_at.isoformat() if it.created_at else "",
					 it.activity_type,
					 it.target_id if it.target_id is not None else "",
					 it.target_name or "",
					 it.rating if it.rating is not None else "",
					])

			elif resource == 'lists':
				writer.writerow([
				 "created_at",
				 "updated_at",
				 "name",
				 "description",
				 "is_public",
				 "albums_count",
				])
				for it in lists_qs[:limit]:
					writer.writerow([
					 it.created_at.isoformat() if it.created_at else "",
					 it.updated_at.isoformat() if it.updated_at else "",
					 it.name,
					 getattr(it, 'description', '') or "",
					 bool(getattr(it, 'is_public', False)),
					 int(getattr(it, 'albums_count', 0) or 0),
					])

			response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
			response['Content-Disposition'] = f'attachment; filename="{filename}"'
			return response

        
		lists_payload = [
		 {
		  "id": int(l.id),
		  "name": l.name,
		  "description": getattr(l, 'description', '') or "",
		  "is_public": bool(getattr(l, 'is_public', False)),
		  "created_at": l.created_at,
		  "updated_at": l.updated_at,
		  "albums_count": int(getattr(l, 'albums_count', 0) or 0),
		 }
		 for l in list(lists_qs[:limit])
		]

		payload = {
		 "generated_at": timezone.now(),
		 "user": {"id": request.user.id, "username": request.user.username},
		 "listens": MyAlbumListenSerializer(listens_qs[:limit], many=True).data,
		 "ratings": MyAlbumRatingSerializer(ratings_qs[:limit], many=True).data,
		 "reviews": MyAlbumReviewSerializer(reviews_qs[:limit], many=True).data,
		 "activity": UserActivitySerializer(activity_qs[:limit], many=True).data,
		 "lists": lists_payload,
		}
		return Response(payload, status=status.HTTP_200_OK)


class MyDataImportView(APIView):
	permission_classes = [IsAuthenticated]
	parser_classes = [MultiPartParser, FormParser]

	def post(self, request):
		fmt = str(request.query_params.get('format', '') or request.data.get('format', '') or '').strip().lower() or 'csv'
		resource = str(request.query_params.get('resource', '') or request.data.get('resource', '') or '').strip().lower()
		if fmt != 'csv':
			return Response({"detail": "Only csv import is supported."}, status=status.HTTP_400_BAD_REQUEST)
		if resource not in {'ratings', 'listens'}:
			return Response({"detail": "resource must be one of: ratings, listens"}, status=status.HTTP_400_BAD_REQUEST)

		upload = request.FILES.get('file') or request.FILES.get('upload')
		if not upload:
			return Response({"detail": "Missing file (multipart field 'file')."}, status=status.HTTP_400_BAD_REQUEST)

                         
		if getattr(upload, 'size', 0) and upload.size > 5 * 1024 * 1024:
			return Response({"detail": "File too large (max 5MB)."}, status=status.HTTP_400_BAD_REQUEST)

		try:
			content = upload.read().decode('utf-8-sig')
		except Exception:
			return Response({"detail": "Could not read file as UTF-8."}, status=status.HTTP_400_BAD_REQUEST)

		reader = csv.DictReader(io.StringIO(content))
		if not reader.fieldnames:
			return Response({"detail": "CSV must include a header row."}, status=status.HTTP_400_BAD_REQUEST)

		processed = 0
		created = 0
		updated = 0
		skipped = 0
		errors = []

		def _get_album(row: dict):
			album_slug = str(row.get('album_slug') or '').strip()
			album_id_raw = str(row.get('album_id') or '').strip()
			qs = Album.objects.filter(is_approved=True, artist__is_approved=True)
			if album_slug:
				return qs.filter(slug=album_slug).first()
			if album_id_raw:
				try:
					album_id = int(album_id_raw)
				except ValueError:
					return None
				return qs.filter(id=album_id).first()
			return None

		with transaction.atomic():
			for idx, row in enumerate(reader, start=2):                    
				processed += 1
				album = _get_album(row)
				if not album:
					skipped += 1
					continue

				if resource == 'ratings':
					rating_raw = str(row.get('rating') or '').strip()
					try:
						rating = int(float(rating_raw))
					except ValueError:
						errors.append({"line": idx, "detail": "Invalid rating"})
						skipped += 1
						continue
					rating = max(1, min(rating, 5))

					_, was_created = AlbumRating.objects.update_or_create(
					 user=request.user,
					 album=album,
					 defaults={"rating": rating},
					)
					if was_created:
						created += 1
					else:
						updated += 1

				elif resource == 'listens':
					listened_date_raw = str(row.get('listened_date') or '').strip()
					listened_at_raw = str(row.get('listened_at') or '').strip()
					listen_date = None
					listen_at = None
					if listened_at_raw:
						try:
							listen_at = datetime.fromisoformat(listened_at_raw.replace('Z', '+00:00'))
						except ValueError:
							listen_at = None
					if listened_date_raw:
						try:
							listen_date = date.fromisoformat(listened_date_raw)
						except ValueError:
							listen_date = None
					if not listen_date and listen_at:
						listen_date = listen_at.date()
					if not listen_date:
						errors.append({"line": idx, "detail": "Missing listened_date"})
						skipped += 1
						continue

					obj, was_created = AlbumListen.objects.get_or_create(
					 user=request.user,
					 album=album,
					 listened_date=listen_date,
					)
					if listened_at_raw and listen_at:
						AlbumListen.objects.filter(pk=obj.pk).update(listened_at=listen_at)
					if was_created:
						created += 1
					else:
						updated += 1

		payload = {
		 "resource": resource,
		 "processed": int(processed),
		 "created": int(created),
		 "updated": int(updated),
		 "skipped": int(skipped),
		 "errors": errors[:50],
		}
		return Response(payload, status=status.HTTP_200_OK)


class MyFavoriteAlbumsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		payload = {"favorite_albums": favorite_albums_payload_for(request.user)}
		return Response(payload, status=status.HTTP_200_OK)

	def put(self, request):
		serializer = FavoriteAlbumsUpdateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		slots = serializer.validated_data['slots']
		album_ids = [int(v) for v in slots if v is not None]

		albums = {
		 int(a.id): a
		 for a in Album.objects.select_related('artist')
		 .filter(
		  id__in=album_ids,
		  is_approved=True,
		  artist__is_approved=True,
		 )
		}
		if len(albums) != len(set(album_ids)):
			return Response({"detail": "Album invalid"}, status=status.HTTP_400_BAD_REQUEST)

		with transaction.atomic():
			FavoriteAlbum.objects.filter(user=request.user).delete()
			to_create: list[FavoriteAlbum] = []
			for idx, album_id in enumerate(slots, start=1):
				if album_id is None:
					continue
				to_create.append(
				 FavoriteAlbum(
				  user=request.user,
				  album=albums[int(album_id)],
				  position=idx,
				 )
				)
			if to_create:
				FavoriteAlbum.objects.bulk_create(to_create)

		payload = {"favorite_albums": favorite_albums_payload_for(request.user)}
                                         
		FavoriteAlbumItemSerializer(payload["favorite_albums"], many=True).data
		return Response(payload, status=status.HTTP_200_OK)


class MyFavoriteSongsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		payload = {"favorite_songs": favorite_songs_payload_for(request.user)}
		return Response(payload, status=status.HTTP_200_OK)

	def put(self, request):
		serializer = FavoriteSongsUpdateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		slots = serializer.validated_data['slots']
		song_ids = [int(v) for v in slots if v is not None]

		songs = {
		 int(s.id): s
		 for s in Song.objects.select_related('artist', 'album', 'album__artist')
		 .filter(
		  id__in=song_ids,
		  is_approved=True,
		  artist__is_approved=True,
		 )
		 .filter(Q(album__isnull=True) | Q(album__is_approved=True, album__artist__is_approved=True))
		}
		if len(songs) != len(set(song_ids)):
			return Response({"detail": "Song invalid"}, status=status.HTTP_400_BAD_REQUEST)

		with transaction.atomic():
			FavoriteSong.objects.filter(user=request.user).delete()
			to_create: list[FavoriteSong] = []
			for idx, song_id in enumerate(slots, start=1):
				if song_id is None:
					continue
				to_create.append(
				 FavoriteSong(
				  user=request.user,
				  song=songs[int(song_id)],
				  position=idx,
				 )
				)
			if to_create:
				FavoriteSong.objects.bulk_create(to_create)

		payload = {"favorite_songs": favorite_songs_payload_for(request.user)}
		FavoriteSongItemSerializer(payload["favorite_songs"], many=True).data
		return Response(payload, status=status.HTTP_200_OK)


class FriendRequestCreateView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		serializer = FriendRequestCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		receiver_username = str(serializer.validated_data['receiver_username']).strip()
		if not receiver_username:
			return Response({"detail": "receiver_username is required"}, status=status.HTTP_400_BAD_REQUEST)

		User = get_user_model()
		receiver = get_object_or_404(User, username=receiver_username)
		if receiver.id == request.user.id:
			return Response({"detail": "Cannot send a friend request to yourself"}, status=status.HTTP_400_BAD_REQUEST)

		existing = (
		 FriendRequest.objects.filter(
		  Q(sender=request.user, receiver=receiver) | Q(sender=receiver, receiver=request.user)
		 )
		 .order_by('-created_at')
		 .first()
		)
		if existing:
			if existing.status == FriendRequest.Status.ACCEPTED:
				return Response({"detail": "Already friends"}, status=status.HTTP_400_BAD_REQUEST)
			if existing.status == FriendRequest.Status.PENDING:
				return Response(FriendRequestSerializer(existing).data, status=status.HTTP_200_OK)
			return Response({"detail": "Friend request already exists"}, status=status.HTTP_400_BAD_REQUEST)

		fr = FriendRequest.objects.create(sender=request.user, receiver=receiver)
		return Response(FriendRequestSerializer(fr).data, status=status.HTTP_201_CREATED)


class FriendRequestAcceptView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		serializer = FriendRequestActionSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		friend_request = get_object_or_404(
		 FriendRequest.objects.select_related('sender', 'receiver'),
		 pk=serializer.validated_data['request_id'],
		 receiver=request.user,
		)
		if friend_request.status != FriendRequest.Status.PENDING:
			return Response({"detail": "Friend request is not pending"}, status=status.HTTP_400_BAD_REQUEST)

		friend_request.status = FriendRequest.Status.ACCEPTED
		friend_request.save(update_fields=['status'])
  
                                                       
		reverse_request, _ = FriendRequest.objects.get_or_create(
		 sender=friend_request.receiver,
		 receiver=friend_request.sender,
		 defaults={'status': FriendRequest.Status.ACCEPTED}
		)
		if reverse_request.status != FriendRequest.Status.ACCEPTED:
			reverse_request.status = FriendRequest.Status.ACCEPTED
			reverse_request.save(update_fields=['status'])
  
		return Response(FriendRequestSerializer(friend_request).data, status=status.HTTP_200_OK)


class FriendRequestRejectView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		serializer = FriendRequestActionSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		friend_request = get_object_or_404(
		 FriendRequest.objects.select_related('sender', 'receiver'),
		 pk=serializer.validated_data['request_id'],
		 receiver=request.user,
		)
		if friend_request.status != FriendRequest.Status.PENDING:
			return Response({"detail": "Friend request is not pending"}, status=status.HTTP_400_BAD_REQUEST)

		friend_request.status = FriendRequest.Status.REJECTED
		friend_request.save(update_fields=['status'])
		return Response(FriendRequestSerializer(friend_request).data, status=status.HTTP_200_OK)


class FriendsListView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		incoming = (
		 FriendRequest.objects.select_related('sender', 'receiver')
		 .filter(receiver=request.user, status=FriendRequest.Status.PENDING)
		 .order_by('-created_at')
		)
		outgoing = (
		 FriendRequest.objects.select_related('sender', 'receiver')
		 .filter(sender=request.user, status=FriendRequest.Status.PENDING)
		 .order_by('-created_at')
		)

                                                  
		accepted = (
		 FriendRequest.objects.select_related('sender', 'receiver')
		 .filter(
		  Q(sender=request.user) | Q(receiver=request.user),
		  status=FriendRequest.Status.ACCEPTED,
		 )
		)

                                                  
		friends_set = set()
		for fr in accepted:
			other = fr.receiver if fr.sender_id == request.user.id else fr.sender
			friends_set.add(other)

                          
		friends = sorted(
		 [{"id": u.id, "username": u.username} for u in friends_set],
		 key=lambda row: row['username'].lower(),
		)
                                                                                        
		if len(friends) == 0:
			friends_payload = []
		else:
			paginator = WantToListenPagination()
			friends_page = paginator.paginate_queryset(friends, request, view=self)
			if friends_page is None:
				friends_payload = {
				 "count": len(friends),
				 "next": None,
				 "previous": None,
				 "results": friends,
				}
			else:
				friends_payload = paginator.get_paginated_response(friends_page).data

		payload = {
		 "friends": friends_payload,
		 "incoming": FriendRequestSerializer(incoming, many=True).data,
		 "outgoing": FriendRequestSerializer(outgoing, many=True).data,
		}
		return Response(payload, status=status.HTTP_200_OK)


class ActivityFeedView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		limit_raw = str(request.query_params.get('limit', '')).strip()
		limit = 50
		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 50
		limit = max(1, min(limit, 100))
		return Response(
		 _serialize_activity_feed(user=request.user, scope='all', limit=limit),
		 status=status.HTTP_200_OK,
		)


class FriendsActivityFeedView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		limit_raw = str(request.query_params.get('limit', '')).strip()
		limit = 50
		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 50
		limit = max(1, min(limit, 100))
		return Response(
		 _serialize_activity_feed(user=request.user, scope='friends', limit=limit),
		 status=status.HTTP_200_OK,
		)


class FollowingActivityFeedView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		limit_raw = str(request.query_params.get('limit', '')).strip()
		limit = 50
		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 50
		limit = max(1, min(limit, 100))
		return Response(
		 _serialize_activity_feed(user=request.user, scope='following', limit=limit),
		 status=status.HTTP_200_OK,
		)


class ConversationsView(APIView):
                                                     
	permission_classes = [IsAuthenticated]

	def get(self, request):
		user = request.user
		from django.db.models import Q, Max, Count, Case, When, Value, BooleanField
  
                                                           
		conversations = {}
  
                         
		sent = ChatMessage.objects.filter(sender=user).select_related('recipient').values('recipient').annotate(
		 last_message_at=Max('created_at'),
		 unread_count=Count('id', filter=Q(is_read=False))
		)
  
                             
		received = ChatMessage.objects.filter(recipient=user).select_related('sender').values('sender').annotate(
		 last_message_at=Max('created_at'),
		 unread_count=Count('id', filter=Q(is_read=False))
		)
  
                       
		user_ids = set()
		for item in sent:
			user_ids.add(item['recipient'])
		for item in received:
			user_ids.add(item['sender'])
  
                           
		from django.contrib.auth import get_user_model
		User = get_user_model()
		result = []
  
		for other_user_id in user_ids:
                                       
			latest = ChatMessage.objects.filter(
			 Q(sender=user, recipient_id=other_user_id) |
			 Q(sender_id=other_user_id, recipient=user)
			).order_by('-created_at').first()
   
			if not latest:
				continue
   
                                           
			unread = ChatMessage.objects.filter(
			 sender_id=other_user_id,
			 recipient=user,
			 is_read=False
			).count()
   
			other_user = User.objects.get(id=other_user_id)
   
			result.append({
			 'user_id': other_user.id,
			 'username': other_user.username,
			 'last_message': latest.content,
			 'last_message_at': latest.created_at,
			 'unread_count': unread,
			 'is_from_current_user': latest.sender_id == user.id,
			})
  
                             
		result.sort(key=lambda x: x['last_message_at'], reverse=True)
  
		serializer = ConversationSummarySerializer(result, many=True)
		return Response(serializer.data, status=status.HTTP_200_OK)


class MessagesWithUserView(APIView):
                                        
	permission_classes = [IsAuthenticated]

	def get(self, request, user_id):
		current_user = request.user
		from django.db.models import Q
		_track_analytics_event(
		 user=current_user,
		 event_name='dm_open',
		 target_type='dm_thread',
		 target_id=int(user_id),
		 properties={'thread_user_id': int(user_id)},
		)
  
                                  
		messages = ChatMessage.objects.filter(
		 Q(sender=current_user, recipient_id=user_id) |
		 Q(sender_id=user_id, recipient=current_user)
		).select_related('sender', 'recipient', 'reply_to', 'reply_to__sender').order_by('created_at')
  
                                  
		unread = ChatMessage.objects.filter(
		 sender_id=user_id,
		 recipient=current_user,
		 is_read=False
		)
		unread.update(is_read=True)
  
		serializer = ChatMessageSerializer(messages, many=True)
		return Response(serializer.data, status=status.HTTP_200_OK)

	def post(self, request, user_id):
                                       
		try:
			current_user = request.user
   
                                                                                
			cutoff = timezone.now() - timedelta(seconds=60)
			recent_count = ChatMessage.objects.filter(sender=current_user, created_at__gte=cutoff).count()
			if recent_count >= 8:
				return Response(
				 {
				  "detail": "Too many messages sent too quickly. Please slow down.",
				  "retry_after_seconds": 60,
				 },
				 status=status.HTTP_429_TOO_MANY_REQUESTS,
				)
   
			if current_user.id == user_id:
				return Response(
				 {'detail': 'Cannot send message to yourself'},
				 status=status.HTTP_400_BAD_REQUEST
				)
   
			from django.contrib.auth import get_user_model
			User = get_user_model()
   
			try:
				recipient = User.objects.get(id=user_id)
			except User.DoesNotExist:
				return Response(
				 {'detail': 'User not found'},
				 status=status.HTTP_404_NOT_FOUND
				)
   
			serializer = ChatMessageCreateSerializer(data=request.data)
			serializer.is_valid(raise_exception=True)

			reply_to = None
			reply_to_id = serializer.validated_data.get('reply_to_id')
			if reply_to_id:
				reply_to = ChatMessage.objects.filter(
				 id=reply_to_id,
				).filter(
				 Q(sender=current_user, recipient=recipient)
				 | Q(sender=recipient, recipient=current_user)
				).first()
				if not reply_to:
					return Response(
					 {'reply_to_id': ['Invalid message for this conversation']},
					 status=status.HTTP_400_BAD_REQUEST,
					)
   
			msg = ChatMessage.objects.create(
			 sender=current_user,
			 recipient=recipient,
			 reply_to=reply_to,
			 content=serializer.validated_data['content'],
			)
   
			_audit_sensitive_action(
			 actor=current_user,
			 action_type=SensitiveActionAudit.ActionType.DM_SENT,
			 target_type='chat_message',
			 target_id=msg.id,
			 summary='Direct message sent',
			 metadata={'recipient_id': int(recipient.id), 'reply_to_id': int(reply_to.id) if reply_to else None},
			)

			return Response(ChatMessageSerializer(msg).data, status=status.HTTP_201_CREATED)
		except Exception as e:
			import traceback
			traceback.print_exc()
			return Response(
			 {'detail': str(e)},
			 status=status.HTTP_500_INTERNAL_SERVER_ERROR
			)


class ChatTypingStatusView(APIView):
                                                 
	permission_classes = [IsAuthenticated]

	def get(self, request, user_id):
		current_user = request.user
		threshold = timezone.now() - timedelta(seconds=8)

		status_obj = ChatTypingStatus.objects.filter(
		 user_id=user_id,
		 partner=current_user,
		 is_typing=True,
		 updated_at__gte=threshold,
		).order_by('-updated_at').first()

		return Response(
		 {
		  'user_id': int(user_id),
		  'is_typing': bool(status_obj),
		 },
		 status=status.HTTP_200_OK,
		)

	def post(self, request, user_id):
		current_user = request.user
		if current_user.id == user_id:
			return Response(
			 {'detail': 'Cannot set typing status for yourself'},
			 status=status.HTTP_400_BAD_REQUEST,
			)

		from django.contrib.auth import get_user_model
		User = get_user_model()
		try:
			partner = User.objects.get(id=user_id)
		except User.DoesNotExist:
			return Response(
			 {'detail': 'User not found'},
			 status=status.HTTP_404_NOT_FOUND,
			)

		serializer = ChatTypingStatusUpdateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		status_obj, _created = ChatTypingStatus.objects.update_or_create(
		 user=current_user,
		 partner=partner,
		 defaults={'is_typing': serializer.validated_data['is_typing']},
		)

		return Response(
		 {
		  'user_id': partner.id,
		  'is_typing': status_obj.is_typing,
		  'updated_at': status_obj.updated_at,
		 },
		 status=status.HTTP_200_OK,
		)


class ChatMessagesView(APIView):
                                                                                       
	permission_classes = [IsAuthenticated]

	def get(self, request):
                                                                
		_track_analytics_event(
		 user=request.user,
		 event_name='dm_open',
		 target_type='dm_inbox',
		 target_id=request.user.id,
		 properties={'view': 'chat_messages'},
		)
		limit_raw = str(request.query_params.get('limit', '')).strip()
		limit = 50
		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 50
		limit = max(1, min(limit, 200))

		from django.db.models import Q
		messages = (
		 ChatMessage.objects.filter(
		  Q(sender=request.user) | Q(recipient=request.user)
		 )
		 .select_related('sender', 'recipient')
		 .order_by('-created_at')[:limit]
		)
		serializer = ChatMessageSerializer(messages, many=True)
		return Response(serializer.data, status=status.HTTP_200_OK)

	def post(self, request):
                                                                     
		content = str(request.data.get('content', '')).strip()
		if not content:
			return Response(
			 {'content': ['Message cannot be empty']},
			 status=status.HTTP_400_BAD_REQUEST,
			)
		if len(content) > 1000:
			return Response(
			 {'content': ['Message is too long']},
			 status=status.HTTP_400_BAD_REQUEST,
			)

		recipient_id = request.data.get('recipient_id')
		from django.contrib.auth import get_user_model
		User = get_user_model()

		if recipient_id in (None, ''):
			recipient = request.user
		else:
			try:
				recipient = User.objects.get(id=recipient_id)
			except (ValueError, TypeError, User.DoesNotExist):
				return Response(
				 {'detail': 'User not found'},
				 status=status.HTTP_404_NOT_FOUND,
				)

		reply_to = None
		reply_to_id = request.data.get('reply_to_id')
		if reply_to_id not in (None, ''):
			try:
				reply_to = ChatMessage.objects.get(id=reply_to_id)
			except (ValueError, TypeError, ChatMessage.DoesNotExist):
				return Response(
				 {'reply_to_id': ['Invalid message']},
				 status=status.HTTP_400_BAD_REQUEST,
				)
  
		msg = ChatMessage.objects.create(
		 sender=request.user,
		 recipient=recipient,
		 reply_to=reply_to,
		 content=content,
		)
		return Response(ChatMessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class CorrectionsView(APIView):
	permission_classes = [AllowAny]

	def post(self, request):
		serializer = CorrectionReportCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		user = request.user if request.user.is_authenticated else None
		report = CorrectionReport.objects.create(
		 user=user,
		 page_url=serializer.validated_data.get('page_url', ''),
		 description=serializer.validated_data['description'],
		)
		return Response(CorrectionReportSerializer(report).data, status=status.HTTP_201_CREATED)


class NotificationsView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		limit_raw = str(request.query_params.get('limit', '')).strip()
		limit = 20
		if limit_raw:
			try:
				limit = int(limit_raw)
			except ValueError:
				limit = 20
		limit = max(1, min(limit, 50))
		return Response(
		 _serialize_notifications_payload(user=request.user, limit=limit),
		 status=status.HTTP_200_OK,
		)


class LiveUpdatesStreamView(APIView):
	permission_classes = [AllowAny]
	authentication_classes = []

	def get(self, request):
		user = _get_user_from_live_token(request.query_params.get('token', ''))
		if not user:
			return Response({'detail': 'Invalid or missing token'}, status=status.HTTP_401_UNAUTHORIZED)

		kind = str(request.query_params.get('kind', 'notifications')).strip().lower()
		if kind not in {'notifications', 'activity'}:
			return Response({'detail': 'Invalid kind'}, status=status.HTTP_400_BAD_REQUEST)

		scope = str(request.query_params.get('scope', 'all')).strip().lower()
		if kind == 'activity' and scope not in {'all', 'friends', 'following'}:
			return Response({'detail': 'Invalid scope'}, status=status.HTTP_400_BAD_REQUEST)

		limit_raw = str(request.query_params.get('limit', '')).strip()
		default_limit = 20 if kind == 'notifications' else 50
		try:
			limit = int(limit_raw) if limit_raw else default_limit
		except ValueError:
			limit = default_limit
		limit = max(1, min(limit, 100))

		interval_raw = str(request.query_params.get('interval', '')).strip()
		try:
			interval = float(interval_raw) if interval_raw else 5.0
		except ValueError:
			interval = 5.0
		interval = max(2.0, min(interval, 30.0))

		def payload_for_current_state():
			if kind == 'notifications':
				return _serialize_notifications_payload(user=user, limit=limit)
			return _serialize_activity_feed(user=user, scope=scope, limit=limit)

		def stream():
			current_payload = payload_for_current_state()
			current_hash = json.dumps(current_payload, ensure_ascii=False, default=str, sort_keys=True)
			yield _sse_event('snapshot', {
			 'kind': kind,
			 'scope': scope,
			 'payload': current_payload,
			})

			while True:
				time.sleep(interval)
				next_payload = payload_for_current_state()
				next_hash = json.dumps(next_payload, ensure_ascii=False, default=str, sort_keys=True)
				if next_hash != current_hash:
					current_hash = next_hash
					yield _sse_event('snapshot', {
					 'kind': kind,
					 'scope': scope,
					 'payload': next_payload,
					})
				yield ': ping\n\n'

		response = StreamingHttpResponse(stream(), content_type='text/event-stream')
		response['Cache-Control'] = 'no-cache, no-transform'
		response['X-Accel-Buffering'] = 'no'
		response['Connection'] = 'keep-alive'
		return response


class NotificationPreferencesView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		prefs, _ = NotificationPreferences.objects.get_or_create(user=request.user)
		return Response(NotificationPreferencesSerializer(prefs).data, status=status.HTTP_200_OK)

	def put(self, request):
		prefs, _ = NotificationPreferences.objects.get_or_create(user=request.user)
		serializer = NotificationPreferencesSerializer(prefs, data=request.data)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(serializer.data, status=status.HTTP_200_OK)

	def patch(self, request):
		prefs, _ = NotificationPreferences.objects.get_or_create(user=request.user)
		serializer = NotificationPreferencesSerializer(prefs, data=request.data, partial=True)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationsDigestView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		prefs, _ = NotificationPreferences.objects.get_or_create(user=request.user)

		window = str(request.query_params.get('window', '')).strip().lower()
		if not window:
			window = prefs.digest_frequency

		if window not in ('daily', 'weekly'):
			return Response(
			 {
			  "enabled": False,
			  "window": prefs.digest_frequency,
			  "digest_channel": prefs.digest_channel,
			  "detail": "Digest is disabled",
			 },
			 status=status.HTTP_200_OK,
			)

		now = timezone.now()
		since = now - (timedelta(days=7) if window == 'weekly' else timedelta(days=1))

		incoming = []
		if prefs.notify_friend_requests:
			incoming = (
			 FriendRequest.objects.select_related('sender', 'receiver')
			 .filter(
			  receiver=request.user,
			  status=FriendRequest.Status.PENDING,
			  created_at__gte=since,
			 )
			 .order_by('-created_at')[:20]
			)

		followed_artist_ids = list(
		 ArtistFollow.objects.filter(user=request.user).values_list('artist_id', flat=True)
		)

		artist_follows = []
		if getattr(prefs, 'notify_artist_follows', True) and followed_artist_ids:
			artist_follows = (
			 ArtistFollow.objects.select_related('user', 'artist')
			 .filter(artist_id__in=followed_artist_ids, created_at__gte=since)
			 .exclude(user=request.user)
			 .order_by('-created_at')[:20]
			)

		followed_artist_releases_payload = []
		if getattr(prefs, 'notify_followed_artist_releases', True) and followed_artist_ids:
			followed_albums = (
			 Album.objects.select_related('artist')
			 .filter(
			  artist_id__in=followed_artist_ids,
			  is_approved=True,
			  artist__is_approved=True,
			  created_at__gte=since,
			  release_date__lte=timezone.localdate(),
			 )
			 .order_by('-created_at', '-id')[:20]
			)
			followed_artist_releases_payload = [
			 _album_release_payload(album=a, reason='followed_artist')
			 for a in followed_albums
			]

		preferred_genre_releases_payload = []
		if getattr(prefs, 'notify_genre_releases', True):
			preferred_genre_ids = _preferred_genre_ids_for_user(user=request.user, limit=5)
			if preferred_genre_ids:
				genre_albums = (
				 Album.objects.select_related('artist')
				 .prefetch_related('genres')
				 .filter(
				  genres__id__in=preferred_genre_ids,
				  is_approved=True,
				  artist__is_approved=True,
				  created_at__gte=since,
				  release_date__lte=timezone.localdate(),
				 )
				 .distinct()
				 .order_by('-created_at', '-id')[:20]
				)
				preferred_set = set(int(x) for x in preferred_genre_ids)
				for album in genre_albums:
					matched_genres = [
					 g.name
					 for g in album.genres.all()
					 if int(g.id) in preferred_set
					]
					preferred_genre_releases_payload.append(
					 _album_release_payload(
					  album=album,
					  reason='preferred_genres',
					  matched_genres=matched_genres,
					 )
					)

		review_likes = []
		if prefs.notify_review_likes:
			review_likes = (
			 AlbumReviewLike.objects.select_related(
			  'user',
			  'review',
			  'review__album',
			  'review__album__artist',
			 )
			 .filter(
			  review__user=request.user,
			  created_at__gte=since,
			 )
			 .exclude(user=request.user)
			 .order_by('-created_at')[:20]
			)

		review_replies = []
		if prefs.notify_review_replies:
			review_replies = (
			 ReviewComment.objects.select_related(
			  'user',
			  'review',
			  'review__album',
			  'review__album__artist',
			 )
			 .filter(
			  review__user=request.user,
			  created_at__gte=since,
			 )
			 .exclude(user=request.user)
			 .order_by('-created_at')[:20]
			)

		mentions = []
		if getattr(prefs, 'notify_mentions', True):
			mentions = (
			 ReviewCommentMention.objects.select_related(
			  'comment',
			  'comment__user',
			  'comment__review',
			  'comment__review__album',
			  'comment__review__album__artist',
			  'mentioned_user',
			 )
			 .filter(mentioned_user=request.user, created_at__gte=since)
			 .exclude(comment__user=request.user)
			 .order_by('-created_at')[:20]
			)

		friends_activity = []
		if prefs.notify_friends_activity:
			accepted = FriendRequest.objects.select_related('sender', 'receiver').filter(
			 Q(sender=request.user) | Q(receiver=request.user),
			 status=FriendRequest.Status.ACCEPTED,
			)
			friend_ids: set[int] = set()
			for fr in accepted:
				other = fr.receiver if fr.sender_id == request.user.id else fr.sender
				friend_ids.add(int(other.id))

			if friend_ids:
				friends_activity = (
				 UserActivity.objects.select_related('actor')
				 .filter(actor_id__in=list(friend_ids), created_at__gte=since)
				 .order_by('-created_at')[:20]
				)

		payload = {
		 "enabled": True,
		 "window": window,
		 "digest_channel": prefs.digest_channel,
		 "from": since,
		 "to": now,
		 "counts": {
		  "friend_requests": len(incoming),
		  "review_likes": len(review_likes),
		  "review_replies": len(review_replies),
		  "mentions": len(mentions),
		  "artist_follows": len(artist_follows),
		  "followed_artist_releases": len(followed_artist_releases_payload),
		  "preferred_genre_releases": len(preferred_genre_releases_payload),
		  "friends_activity": len(friends_activity),
		 },
		 "incoming_friend_requests": FriendRequestSerializer(incoming, many=True).data,
		 "review_likes": AlbumReviewLikeNotificationSerializer(review_likes, many=True).data,
		 "review_replies": ReviewReplyNotificationSerializer(review_replies, many=True).data,
		 "mentions": ReviewMentionNotificationSerializer(mentions, many=True).data,
		 "artist_follows": ArtistFollowNotificationSerializer(artist_follows, many=True).data,
		 "followed_artist_releases": AlbumReleaseNotificationSerializer(followed_artist_releases_payload, many=True).data,
		 "preferred_genre_releases": AlbumReleaseNotificationSerializer(preferred_genre_releases_payload, many=True).data,
		 "friends_activity": UserActivitySerializer(friends_activity, many=True).data,
		}
		return Response(payload, status=status.HTTP_200_OK)


class ReviewCommentReactionsView(APIView):
                                          
	permission_classes = [IsAuthenticated]

	def get(self, request, comment_id):
		try:
			comment = ReviewComment.objects.get(id=comment_id)
		except ReviewComment.DoesNotExist:
			return Response(
			 {'detail': 'Comment not found'},
			 status=status.HTTP_404_NOT_FOUND
			)

                                            
		reactions = ReviewCommentReaction.objects.filter(comment=comment).values('emoji').annotate(count=Count('id'))
  
                                                        
		user_reactions = set()
		if request.user.is_authenticated:
			user_reactions = set(
			 ReviewCommentReaction.objects.filter(
			  comment=comment,
			  user=request.user
			 ).values_list('emoji', flat=True)
			)

		result = []
		for reaction in reactions:
			result.append({
			 'emoji': reaction['emoji'],
			 'count': reaction['count'],
			 'user_reacted': reaction['emoji'] in user_reactions,
			})

		serializer = ReactionsSummarySerializer(result, many=True)
		return Response(serializer.data, status=status.HTTP_200_OK)


class ReviewCommentReactionView(APIView):
                                                   
	permission_classes = [IsAuthenticated]

	def post(self, request, comment_id):
		try:
			comment = ReviewComment.objects.get(id=comment_id)
		except ReviewComment.DoesNotExist:
			return Response(
			 {'detail': 'Comment not found'},
			 status=status.HTTP_404_NOT_FOUND
			)

		serializer = ReviewCommentReactionCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		emoji = serializer.validated_data['emoji']

                                                 
		reaction, created = ReviewCommentReaction.objects.get_or_create(
		 user=request.user,
		 comment=comment,
		 emoji=emoji,
		)

		if not created:
                                               
			reaction.delete()
			return Response({'detail': 'Reaction removed'}, status=status.HTTP_200_OK)

		return Response(ReviewCommentReactionSerializer(reaction).data, status=status.HTTP_201_CREATED)


class SongCommentReactionsView(APIView):
                                               
	permission_classes = [IsAuthenticated]

	def get(self, request, comment_id):
		try:
			comment = SongComment.objects.get(id=comment_id)
		except SongComment.DoesNotExist:
			return Response(
			 {'detail': 'Comment not found'},
			 status=status.HTTP_404_NOT_FOUND
			)

                                            
		reactions = SongCommentReaction.objects.filter(comment=comment).values('emoji').annotate(count=Count('id'))
  
                                                        
		user_reactions = set()
		if request.user.is_authenticated:
			user_reactions = set(
			 SongCommentReaction.objects.filter(
			  comment=comment,
			  user=request.user
			 ).values_list('emoji', flat=True)
			)

		result = []
		for reaction in reactions:
			result.append({
			 'emoji': reaction['emoji'],
			 'count': reaction['count'],
			 'user_reacted': reaction['emoji'] in user_reactions,
			})

		serializer = ReactionsSummarySerializer(result, many=True)
		return Response(serializer.data, status=status.HTTP_200_OK)


class SongCommentReactionView(APIView):
                                                 
	permission_classes = [IsAuthenticated]

	def post(self, request, comment_id):
		try:
			comment = SongComment.objects.get(id=comment_id)
		except SongComment.DoesNotExist:
			return Response(
			 {'detail': 'Comment not found'},
			 status=status.HTTP_404_NOT_FOUND
			)

		serializer = SongCommentReactionCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		emoji = serializer.validated_data['emoji']

                                                 
		reaction, created = SongCommentReaction.objects.get_or_create(
		 user=request.user,
		 comment=comment,
		 emoji=emoji,
		)

		if not created:
                                               
			reaction.delete()
			return Response({'detail': 'Reaction removed'}, status=status.HTTP_200_OK)

		return Response(SongCommentReactionSerializer(reaction).data, status=status.HTTP_201_CREATED)


class UserOnboardingSetupView(APIView):
                                                                    
	permission_classes = [IsAuthenticated]

	def post(self, request):
                                                                
		serializer = UserOnboardingCompleteSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)

		genre_ids = serializer.validated_data.get('genre_ids', [])
		artist_ids = serializer.validated_data.get('artist_ids', [])

                                          
		existing_genres = set(Genre.objects.filter(id__in=genre_ids).values_list('id', flat=True))
		existing_artists = set(Artist.objects.filter(id__in=artist_ids).values_list('id', flat=True))

		invalid_genres = set(genre_ids) - existing_genres
		invalid_artists = set(artist_ids) - existing_artists

		if invalid_genres or invalid_artists:
			errors = {}
			if invalid_genres:
				errors['invalid_genres'] = list(invalid_genres)
			if invalid_artists:
				errors['invalid_artists'] = list(invalid_artists)
			return Response(errors, status=status.HTTP_400_BAD_REQUEST)

                                   
		now = timezone.now()
		onboarding, created = UserOnboarding.objects.get_or_create(user=request.user)
		onboarding.is_completed = True
		onboarding.completed_at = now
		onboarding.save()
		onboarding.preferred_genres.set(genre_ids)
		onboarding.preferred_artists.set(artist_ids)
		_track_analytics_event(
		 user=request.user,
		 event_name='onboarding_completed',
		 target_type='onboarding',
		 target_id=onboarding.id,
		 properties={'genre_ids': [int(g) for g in genre_ids], 'artist_ids': [int(a) for a in artist_ids]},
		)

		payload = {
		 'success': True,
		 'message': 'Onboarding completed',
		 'onboarding': UserOnboardingSerializer(onboarding).data,
		}
		return Response(payload, status=status.HTTP_200_OK)

	def get(self, request):
                                                                        
		try:
			onboarding = UserOnboarding.objects.get(user=request.user)
			serializer = UserOnboardingSerializer(onboarding)
			return Response(serializer.data, status=status.HTTP_200_OK)
		except UserOnboarding.DoesNotExist:
                                       
			return Response(
			 {'is_completed': False, 'completed_at': None},
			 status=status.HTTP_200_OK
			)


class AnalyticsEventsView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		event_name = str(request.data.get('event_name', '')).strip()
		if not event_name:
			return Response({'event_name': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)

		target_type = str(request.data.get('target_type', '')).strip()
		target_id = request.data.get('target_id')
		properties = request.data.get('properties')
		if not isinstance(properties, dict):
			properties = {}

		_track_analytics_event(
		 user=request.user,
		 event_name=event_name,
		 target_type=target_type,
		 target_id=target_id,
		 properties=properties,
		)
		return Response({'ok': True}, status=status.HTTP_201_CREATED)


class AnalyticsKpisView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		if not request.user.is_staff:
			return Response(status=status.HTTP_403_FORBIDDEN)

		days = _parse_days_window(request.query_params.get('days', '30'))
		metrics = _analytics_metrics_for_window(days=days)
		definitions = [
		 {'key': 'd1_retention_pct', 'label': 'D1 retention', 'definition': 'Percentage of home-view users who returned the next day.'},
		 {'key': 'd7_retention_pct', 'label': 'D7 retention', 'definition': 'Percentage of home-view users who returned seven days later.'},
		 {'key': 'reviews_per_user', 'label': 'Reviews per user', 'definition': 'Average review count per user with at least one review in the selected window.'},
		 {'key': 'comments_per_review', 'label': 'Comments per review', 'definition': 'Average number of review comments per review in the selected window.'},
		 {'key': 'dm_opens', 'label': 'DM opens', 'definition': 'Total direct-message thread opens in the selected window.'},
		 {'key': 'weekly_active_users', 'label': 'Weekly active users', 'definition': 'Distinct users active in the last seven days of the selected window.'},
		]
		return Response({'window_days': days, 'definitions': definitions, 'metrics': metrics}, status=status.HTTP_200_OK)


class WeeklyRecapView(APIView):
                                                                              
	permission_classes = [IsAuthenticated]

	def get(self, request):
                                                  
		user = request.user
		now = timezone.now()
		week_ago = now - timedelta(days=7)

                                      
		top_listens = (
		 AlbumListen.objects.filter(user=user, listened_at__gte=week_ago)
		 .values('album')
		 .annotate(listen_count=Count('id'))
		 .order_by('-listen_count')[:5]
		)
		top_listens_ids = [item['album'] for item in top_listens]
		top_listens_data = []
		if top_listens_ids:
			albums = Album.objects.select_related('artist').filter(id__in=top_listens_ids)
			album_map = {album.id: album for album in albums}
			for item in top_listens:
				album = album_map.get(item['album'])
				if album:
					top_listens_data.append({
					 'id': album.id,
					 'slug': album.slug,
					 'title': album.title,
					 'artist': album.artist.name,
					 'listen_count': item['listen_count'],
					})

                     
		streak_payload = streak_payload_for(user)

                                     
		new_friends = (
		 FriendRequest.objects.select_related('sender', 'receiver')
		 .filter(
		  Q(sender=user) | Q(receiver=user),
		  status=FriendRequest.Status.ACCEPTED,
		  created_at__gte=week_ago,
		 )
		 .order_by('-created_at')[:5]
		)
		new_friends_data = []
		for fr in new_friends:
			friend = fr.receiver if fr.sender_id == user.id else fr.sender
			new_friends_data.append({
			 'id': friend.id,
			 'username': friend.username,
			 'first_name': friend.first_name,
			})

                                                                 
		accepted = FriendRequest.objects.select_related('sender', 'receiver').filter(
		 Q(sender=user) | Q(receiver=user),
		 status=FriendRequest.Status.ACCEPTED,
		)
		friend_ids: set[int] = set()
		for fr in accepted:
			other = fr.receiver if fr.sender_id == user.id else fr.sender
			friend_ids.add(int(other.id))

		top_reviews = []
		if friend_ids:
			top_reviews = (
			 AlbumReview.objects.select_related('album', 'album__artist', 'user')
			 .filter(user_id__in=list(friend_ids), created_at__gte=week_ago)
			 .annotate(
			  engagement=Count('likes', distinct=True) + Count('comments', distinct=True),
			 )
			 .order_by('-engagement')[:5]
			)
			top_reviews_data = []
			for review in top_reviews:
				top_reviews_data.append({
				 'id': review.id,
				 'album_id': review.album.id,
				 'album_slug': review.album.slug,
				 'album_title': review.album.title,
				 'artist_name': review.album.artist.name,
				 'user_id': review.user.id,
				 'username': review.user.username,
				 'rating': None,
				 'text': review.content[:200] if review.content else '',
				 'likes_count': review.likes.count(),
				 'comments_count': review.comments.count(),
				})
		else:
			top_reviews_data = []

		payload = {
		 'week_from': week_ago.isoformat(),
		 'week_to': now.isoformat(),
		 'top_listens': top_listens_data,
		 'streak': streak_payload.get('current_streak', 0),
		 'new_friends_count': len(new_friends_data),
		 'new_friends': new_friends_data,
		 'top_reviews': top_reviews_data,
		 'weekly_challenges': weekly_challenges_payload_for(user),
		}
		return Response(payload, status=status.HTTP_200_OK)
