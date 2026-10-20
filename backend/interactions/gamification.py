from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.utils import timezone

from interactions.models import (
 AlbumLike,
 AlbumListen,
 AlbumRating,
 AlbumReview,
 ArtistFollow,
 List as UserList,
 FriendRequest,
 ListAlbum,
 SongRating,
 UserActivity,
)


@dataclass(frozen=True)
class WeekBounds:
	start: date
	end: date


def current_week_bounds(today: date | None = None) -> WeekBounds:
                                                               
	if today is None:
		today = timezone.localdate()
	start = today - timedelta(days=int(today.weekday()))              
	end = start + timedelta(days=6)
	return WeekBounds(start=start, end=end)


def _week_window_bounds(today: date | None = None) -> tuple[WeekBounds, WeekBounds]:
	current = current_week_bounds(today)
	previous_start = current.start - timedelta(days=7)
	previous = WeekBounds(start=previous_start, end=previous_start + timedelta(days=6))
	return current, previous


def _date_filter_for_week(start: date, end: date, field_name: str = 'created_at') -> dict:
	return {
	 f'{field_name}__date__gte': start,
	 f'{field_name}__date__lte': end,
	}


def _week_start_index(bounds: WeekBounds, size: int) -> int:
	if size <= 0:
		return 0
	return int(bounds.start.toordinal() % size)


def _count_romanian_album_listens(user, start: date, end: date) -> int:
	return int(
	 AlbumListen.objects.filter(
	  user=user,
	  album__is_approved=True,
	  album__artist__is_approved=True,
	  listened_date__gte=start,
	  listened_date__lte=end,
	 )
	 .values('album_id')
	 .distinct()
	 .count()
	)


def _count_90s_album_listens(user, start: date, end: date) -> int:
	return int(
	 AlbumListen.objects.filter(
	  user=user,
	  album__is_approved=True,
	  album__artist__is_approved=True,
	  album__release_date__year__gte=1990,
	  album__release_date__year__lte=1999,
	  listened_date__gte=start,
	  listened_date__lte=end,
	 )
	 .values('album_id')
	 .distinct()
	 .count()
	)


def _count_listened_genres(user, start: date, end: date) -> int:
	return int(
	 AlbumListen.objects.filter(
	  user=user,
	  album__is_approved=True,
	  album__artist__is_approved=True,
	  listened_date__gte=start,
	  listened_date__lte=end,
	  album__genres__isnull=False,
	 )
	 .values('album__genres__id')
	 .distinct()
	 .count()
	)


def _count_album_reviews(user, start: date, end: date) -> int:
	return int(
	 AlbumReview.objects.filter(
	  user=user,
	  album__is_approved=True,
	  album__artist__is_approved=True,
	  **_date_filter_for_week(start, end),
	 )
	 .count()
	)


def _count_album_ratings(user, start: date, end: date) -> int:
	return int(
	 AlbumRating.objects.filter(
	  user=user,
	  album__is_approved=True,
	  album__artist__is_approved=True,
	  **_date_filter_for_week(start, end),
	 )
	 .count()
	)


def _count_album_likes(user, start: date, end: date) -> int:
	return int(
	 AlbumLike.objects.filter(
	  user=user,
	  album__is_approved=True,
	  album__artist__is_approved=True,
	  **_date_filter_for_week(start, end),
	 )
	 .count()
	)


def _count_created_lists(user, start: date, end: date) -> int:
	return int(
	 UserList.objects.filter(
	  user=user,
	  **_date_filter_for_week(start, end),
	 )
	 .count()
	)


def _count_followed_artists(user, start: date, end: date) -> int:
	return int(
	 ArtistFollow.objects.filter(
	  user=user,
	  **_date_filter_for_week(start, end),
	 )
	 .count()
	)


def _count_list_album_additions(user, start: date, end: date) -> int:
	return int(
	 ListAlbum.objects.filter(
	  list__user=user,
	  **_date_filter_for_week(start, end, field_name='added_at'),
	 )
	 .count()
	)


def _count_song_ratings(user, start: date, end: date) -> int:
	return int(
	 SongRating.objects.filter(
	  user=user,
	  song__is_approved=True,
	  song__artist__is_approved=True,
	  **_date_filter_for_week(start, end),
	 )
	 .count()
	)


def _count_new_friends(user, start: date, end: date) -> int:
	return int(
	 FriendRequest.objects.filter(
	  Q_sender_or_receiver(user),
	  status=FriendRequest.Status.ACCEPTED,
	  **_date_filter_for_week(start, end),
	 )
	 .count()
	)


def Q_sender_or_receiver(user):
	from django.db.models import Q

	return Q(sender=user) | Q(receiver=user)


def _weekly_challenge_templates() -> list[dict]:
	return [
	 {
	  "key": "listen_romanian_3",
	  "title": "Albume românești",
	  "description": "Ascultă 3 albume de la artiști români săptămâna asta",
	  "target": 3,
	  "progress_fn": _count_romanian_album_listens,
	 },
	 {
	  "key": "listen_90s_1",
	  "title": "Anii '90",
	  "description": "Ascultă 1 album lansat în anii 1990",
	  "target": 1,
	  "progress_fn": _count_90s_album_listens,
	 },
	 {
	  "key": "genres_3",
	  "title": "Explorator de genuri",
	  "description": "Ascultă albume din 3 genuri diferite săptămâna asta",
	  "target": 3,
	  "progress_fn": _count_listened_genres,
	 },
	 {
	  "key": "review_2",
	  "title": "Critic activ",
	  "description": "Scrie 2 review-uri noi săptămâna asta",
	  "target": 2,
	  "progress_fn": _count_album_reviews,
	 },
	 {
	  "key": "rating_5",
	  "title": "Notează muzica",
	  "description": "Oferă 5 ratinguri noi albumelelor săptămâna asta",
	  "target": 5,
	  "progress_fn": _count_album_ratings,
	 },
	 {
	  "key": "like_5",
	  "title": "Colecționar de like-uri",
	  "description": "Dă like la 5 albume săptămâna asta",
	  "target": 5,
	  "progress_fn": _count_album_likes,
	 },
	 {
	  "key": "create_list_1",
	  "title": "Listă nouă",
	  "description": "Creează o listă nouă săptămâna asta",
	  "target": 1,
	  "progress_fn": _count_created_lists,
	 },
	 {
	  "key": "follow_artist_2",
	  "title": "Urmărește artiști",
	  "description": "Urmărește 2 artiști noi săptămâna asta",
	  "target": 2,
	  "progress_fn": _count_followed_artists,
	 },
	 {
	  "key": "list_add_album_5",
	  "title": "Curator activ",
	  "description": "Adaugă 5 albume în liste săptămâna asta",
	  "target": 5,
	  "progress_fn": _count_list_album_additions,
	 },
	 {
	  "key": "song_rating_5",
	  "title": "Notează piese",
	  "description": "Oferă rating la 5 piese săptămâna asta",
	  "target": 5,
	  "progress_fn": _count_song_ratings,
	 },
	 {
	  "key": "friend_1",
	  "title": "Gusturi împărtășite",
	  "description": "Adaugă un prieten nou săptămâna asta",
	  "target": 1,
	  "progress_fn": _count_new_friends,
	 },
	]


def _selected_weekly_templates(bounds: WeekBounds, count: int = 3) -> list[dict]:
	templates = list(_weekly_challenge_templates())
	if not templates:
		return []
	start_index = _week_start_index(bounds, len(templates))
	selected = []
	for offset in range(min(count, len(templates))):
		selected.append(templates[(start_index + offset) % len(templates)])
	return selected


def _build_weekly_challenge_entry(template: dict, user, week_start: date, week_end: date) -> dict:
	progress_fn = template.get('progress_fn')
	progress = 0
	if callable(progress_fn):
		progress = int(progress_fn(user, week_start, week_end))
	target = int(template.get('target') or 0)
	completed = progress >= target
	return {
	 "key": template.get('key', ''),
	 "title": template.get('title', ''),
	 "description": template.get('description', ''),
	 "progress": int(progress),
	 "target": target,
	 "completed": bool(completed),
	}


def weekly_challenge_window_payload_for(user, week_bounds: WeekBounds) -> dict:
	selected = _selected_weekly_templates(week_bounds)
	challenges = [
	 _build_weekly_challenge_entry(template, user, week_bounds.start, week_bounds.end)
	 for template in selected
	]
	completed_challenges = [c for c in challenges if c['completed']]
	incomplete_challenges = [c for c in challenges if not c['completed']]
	return {
	 "week_start": week_bounds.start.isoformat(),
	 "week_end": week_bounds.end.isoformat(),
	 "challenges": challenges,
	 "completed_challenges": completed_challenges,
	 "incomplete_challenges": incomplete_challenges,
	 "completed_count": len(completed_challenges),
	 "incomplete_count": len(incomplete_challenges),
	 "total_count": len(challenges),
	 "completion_rate": int(round((len(completed_challenges) / len(challenges)) * 100)) if challenges else 0,
	}


def _distinct_dates_desc(dates: list[date]) -> list[date]:
	seen = set()
	out: list[date] = []
	for d in sorted([d for d in dates if isinstance(d, date)], reverse=True):
		if d in seen:
			continue
		seen.add(d)
		out.append(d)
	return out


def _consecutive_streak_from(today: date, days_desc: list[date]) -> int:
                                                                           
	if not days_desc:
		return 0

	streak = 0
	cursor = today
	date_set = set(days_desc)
	while cursor in date_set:
		streak += 1
		cursor = cursor - timedelta(days=1)
	return streak


def streak_payload_for(user, today: date | None = None) -> dict:
	if today is None:
		today = timezone.localdate()

	listen_days = list(
	 AlbumListen.objects.filter(
	  user=user,
	  album__is_approved=True,
	  album__artist__is_approved=True,
	  listened_date__lte=today,
	 )
	 .values_list('listened_date', flat=True)
	 .distinct()
	)

                                                                             
	rating_days = [
	 (dt.date() if hasattr(dt, 'date') else dt)
	 for dt in UserActivity.objects.filter(
	  actor=user,
	  activity_type=UserActivity.Type.RATE_ALBUM,
	  created_at__date__lte=today,
	 )
	 .values_list('created_at', flat=True)
	]

	combined_days = _distinct_dates_desc(
	 [d for d in listen_days if isinstance(d, date)]
	 + [d for d in rating_days if isinstance(d, date)]
	)
	listen_days_desc = _distinct_dates_desc([d for d in listen_days if isinstance(d, date)])
	rating_days_desc = _distinct_dates_desc([d for d in rating_days if isinstance(d, date)])

	return {
	 "today": today.isoformat(),
	 "listen_streak_days": int(_consecutive_streak_from(today, listen_days_desc)),
	 "rating_streak_days": int(_consecutive_streak_from(today, rating_days_desc)),
	 "activity_streak_days": int(_consecutive_streak_from(today, combined_days)),
	}


def weekly_challenges_payload_for(user, today: date | None = None) -> dict:
	if today is None:
		today = timezone.localdate()

	current_bounds, previous_bounds = _week_window_bounds(today)
	current_week = weekly_challenge_window_payload_for(user, current_bounds)
	previous_week = weekly_challenge_window_payload_for(user, previous_bounds)

	return {
	 "week_start": current_bounds.start.isoformat(),
	 "week_end": current_bounds.end.isoformat(),
	 "today": today.isoformat(),
	 "challenges": current_week['challenges'],
	 "completed_challenges": current_week['completed_challenges'],
	 "incomplete_challenges": current_week['incomplete_challenges'],
	 "completed_count": current_week['completed_count'],
	 "incomplete_count": current_week['incomplete_count'],
	 "total_count": current_week['total_count'],
	 "completion_rate": current_week['completion_rate'],
	 "previous_week_recap": previous_week,
	}
