"""
Achievement Progress Tracking System

Handles:
- Tracking user progress towards achievements
- Auto-unlocking achievements when targets are met
- Awarding XP points to users
- Maintaining achievement progress state
"""

from datetime import timedelta
from django.utils import timezone
from django.db import transaction

from interactions.models import (
	UserAchievement,
	Achievement,
	UserXP,
	AlbumReview,
	AlbumRating,
	AlbumLike,
	AlbumListen,
	ArtistFollow,
	List as UserList,
	AchievementUnlock,
)


def get_or_create_achievement(user, achievement_code: str) -> UserAchievement:
	"""Get or create UserAchievement for a user."""
	try:
		achievement = Achievement.objects.get(code=achievement_code)
	except Achievement.DoesNotExist:
		return None
	
	user_achievement, created = UserAchievement.objects.get_or_create(
		user=user,
		achievement=achievement,
		defaults={'progress': 0, 'is_completed': False}
	)
	return user_achievement


def increment_achievement_progress(user, achievement_code: str, increment: int = 1) -> tuple[UserAchievement, bool]:
	"""
	Increment achievement progress and auto-unlock if target is met.
	
	Returns:
		(UserAchievement, was_unlocked: bool)
	"""
	user_achievement = get_or_create_achievement(user, achievement_code)
	if not user_achievement:
		return None, False
	
	# Don't increment if already completed
	if user_achievement.is_completed:
		return user_achievement, False
	
	# Increment progress
	user_achievement.progress = min(
		user_achievement.progress + increment,
		user_achievement.achievement.target
	)
	
	was_unlocked = False
	
	# Check if target reached
	if user_achievement.progress >= user_achievement.achievement.target:
		user_achievement.is_completed = True
		user_achievement.unlocked_at = timezone.now()
		was_unlocked = True
		
		# Award XP to user
		award_xp_for_achievement(user, user_achievement.achievement)
	
	user_achievement.save()
	return user_achievement, was_unlocked


def award_xp_for_achievement(user, achievement: Achievement) -> UserXP:
	"""
	Award XP points to user for completing an achievement.
	
	Returns:
		Updated UserXP object
	"""
	with transaction.atomic():
		user_xp, _ = UserXP.objects.get_or_create(
			user=user,
			defaults={'total_xp': 0, 'level': 1, 'current_level_xp': 0}
		)
		user_xp.add_xp(achievement.points)
		
		# Create unlock notification
		_notify_achievement_unlock(user, achievement)
		
		return user_xp


def _notify_achievement_unlock(user, achievement: Achievement):
	"""Create an achievement unlock notification record."""
	try:
		AchievementUnlock.objects.create(
			user=user,
			achievement=achievement,
			achievement_code=achievement.code,
			achievement_name=achievement.name,
			achievement_emoji=achievement.emoji,
			xp_awarded=achievement.points,
		)
	except Exception as e:
		# Log but don't fail if notification creation fails
		import logging
		logger = logging.getLogger(__name__)
		logger.error(f"Failed to create achievement unlock notification: {e}")


# ============================================================================
# STREAK ACHIEVEMENTS
# ============================================================================

def track_review_streak(user) -> bool:
	"""
	Track if user maintains a review posting streak.
	Achievement: 'review_streak_5' - Post reviews for 5 consecutive days
	"""
	return track_daily_activity_streak(user, 'review_streak_5', 5, 'reviews')


def track_listen_streak(user) -> bool:
	"""
	Track if user maintains a listening streak.
	Achievement: 'listen_streak_7' - Listen to albums for 7 consecutive days
	"""
	return track_daily_activity_streak(user, 'listen_streak_7', 7, 'listens')


def track_rating_streak(user) -> bool:
	"""
	Track if user maintains a rating streak.
	Achievement: 'rating_streak_3' - Rate albums for 3 consecutive days
	"""
	return track_daily_activity_streak(user, 'rating_streak_3', 3, 'ratings')


def track_daily_activity_streak(user, achievement_code: str, target_days: int, activity_type: str) -> bool:
	"""
	Generic daily activity streak tracker.
	
	Args:
		user: User object
		achievement_code: Code of the achievement to track
		target_days: Number of consecutive days needed
		activity_type: Type of activity ('reviews', 'listens', 'ratings')
	
	Returns:
		bool: Whether achievement was unlocked
	"""
	user_achievement = get_or_create_achievement(user, achievement_code)
	if not user_achievement or user_achievement.is_completed:
		return False
	
	# Count consecutive days with activity
	consecutive_days = count_consecutive_activity_days(user, activity_type)
	
	# Update progress
	user_achievement.progress = consecutive_days
	was_unlocked = False
	
	if consecutive_days >= target_days:
		user_achievement.is_completed = True
		user_achievement.unlocked_at = timezone.now()
		was_unlocked = True
		award_xp_for_achievement(user, user_achievement.achievement)
	
	user_achievement.save()
	return was_unlocked


def count_consecutive_activity_days(user, activity_type: str) -> int:
	"""Count consecutive days of activity for a user."""
	today = timezone.localdate()
	consecutive = 0
	
	for i in range(30):  # Check last 30 days max
		check_date = today - timedelta(days=i)
		
		if activity_type == 'reviews':
			has_activity = AlbumReview.objects.filter(
				user=user,
				created_at__date=check_date
			).exists()
		elif activity_type == 'listens':
			has_activity = AlbumListen.objects.filter(
				user=user,
				listened_date=check_date
			).exists()
		elif activity_type == 'ratings':
			has_activity = AlbumRating.objects.filter(
				user=user,
				created_at__date=check_date
			).exists()
		else:
			has_activity = False
		
		if has_activity:
			consecutive += 1
		else:
			break  # Streak broken
	
	return consecutive


# ============================================================================
# MILESTONE ACHIEVEMENTS
# ============================================================================

def track_review_milestone(user) -> bool:
	"""
	Track total reviews written.
	Achievement: 'reviewer_5' - Write 5 album reviews
	"""
	review_count = AlbumReview.objects.filter(user=user).count()
	user_achievement, was_unlocked = increment_achievement_progress(
		user, 'reviewer_5', review_count
	)
	return was_unlocked


def track_rating_milestone(user) -> bool:
	"""
	Track total ratings given.
	Achievement: 'rater_10' - Rate 10 albums
	"""
	rating_count = AlbumRating.objects.filter(user=user).count()
	user_achievement, was_unlocked = increment_achievement_progress(
		user, 'rater_10', rating_count
	)
	return was_unlocked


def track_listen_milestone(user) -> bool:
	"""
	Track total distinct albums listened.
	Achievement: 'listener_50' - Listen to 50 distinct albums
	"""
	listen_count = AlbumListen.objects.filter(
		user=user
	).values('album_id').distinct().count()
	
	user_achievement, was_unlocked = increment_achievement_progress(
		user, 'listener_50', listen_count
	)
	return was_unlocked


def track_follow_milestone(user) -> bool:
	"""
	Track total artists followed.
	Achievement: 'fan_20' - Follow 20 artists
	"""
	follow_count = ArtistFollow.objects.filter(user=user).count()
	user_achievement, was_unlocked = increment_achievement_progress(
		user, 'fan_20', follow_count
	)
	return was_unlocked


# ============================================================================
# SOCIAL ACHIEVEMENTS
# ============================================================================

def track_liker_milestone(user) -> bool:
	"""
	Track total likes given.
	Achievement: 'liker_25' - Like 25 albums
	"""
	like_count = AlbumLike.objects.filter(user=user).count()
	user_achievement, was_unlocked = increment_achievement_progress(
		user, 'liker_25', like_count
	)
	return was_unlocked


def track_list_creator(user) -> bool:
	"""
	Track if user created first list.
	Achievement: 'list_creator' - Create your first list
	"""
	has_list = UserList.objects.filter(user=user).exists()
	if has_list:
		user_achievement, was_unlocked = increment_achievement_progress(
			user, 'list_creator', 1
		)
		return was_unlocked
	return False


# ============================================================================
# DISCOVERY ACHIEVEMENTS
# ============================================================================

def track_romanian_explorer(user) -> bool:
	"""
	Track listening to Romanian artists.
	Achievement: 'romanian_explorer' - Listen to 10 Romanian artists
	"""
	from music.models import Artist
	
	# Count distinct Romanian artists where the user listened to any of their albums.
	# Album listens use related_name='listens' on Album, and Album has related_name='albums' on Artist.
	romanian_artists = Artist.objects.filter(
		is_romanian=True,
		albums__listens__user=user
	).distinct().count()
	
	user_achievement, was_unlocked = increment_achievement_progress(
		user, 'romanian_explorer', romanian_artists
	)
	return was_unlocked


def track_genre_explorer(user) -> bool:
	"""
	Track listening across genres.
	Achievement: 'genre_explorer' - Listen to albums from 15 different genres
	"""
	genre_count = AlbumListen.objects.filter(
		user=user
	).values('album__genres__id').distinct().count()
	
	user_achievement, was_unlocked = increment_achievement_progress(
		user, 'genre_explorer', genre_count
	)
	return was_unlocked


def track_era_explorer(user) -> bool:
	"""
	Track listening to music from different eras.
	Achievement: 'era_explorer' - Listen to albums from 5 different decades
	"""
	from django.db.models import F, Value
	from django.db.models.functions import ExtractYear
	from math import floor
	
	decades = set()
	albums = AlbumListen.objects.filter(
		user=user
	).values('album__release_date').distinct()
	
	for item in albums:
		if item['album__release_date']:
			year = item['album__release_date'].year
			decade = floor(year / 10) * 10
			decades.add(decade)
	
	user_achievement, was_unlocked = increment_achievement_progress(
		user, 'era_explorer', len(decades)
	)
	return was_unlocked


# ============================================================================
# BATCH UPDATE FUNCTIONS (for periodic tasks)
# ============================================================================

def update_all_achievement_progress(user):
	"""
	Batch update all achievements for a user.
	Call this periodically to sync achievement progress.
	"""
	unlocked_achievements = []
	
	# Update all achievement types
	if track_review_milestone(user):
		unlocked_achievements.append('reviewer_5')
	if track_rating_milestone(user):
		unlocked_achievements.append('rater_10')
	if track_listen_milestone(user):
		unlocked_achievements.append('listener_50')
	if track_follow_milestone(user):
		unlocked_achievements.append('fan_20')
	if track_liker_milestone(user):
		unlocked_achievements.append('liker_25')
	if track_list_creator(user):
		unlocked_achievements.append('list_creator')
	if track_romanian_explorer(user):
		unlocked_achievements.append('romanian_explorer')
	if track_genre_explorer(user):
		unlocked_achievements.append('genre_explorer')
	if track_era_explorer(user):
		unlocked_achievements.append('era_explorer')
	if track_review_streak(user):
		unlocked_achievements.append('review_streak_5')
	if track_listen_streak(user):
		unlocked_achievements.append('listen_streak_7')
	if track_rating_streak(user):
		unlocked_achievements.append('rating_streak_3')
	
	return unlocked_achievements
