\
\
\
\
\
\
\
\
   

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
\
\
\
\
\
    
	user_achievement = get_or_create_achievement(user, achievement_code)
	if not user_achievement:
		return None, False
 
                                       
	if user_achievement.is_completed:
		return user_achievement, False
 
                     
	user_achievement.progress = min(
	 user_achievement.progress + increment,
	 user_achievement.achievement.target
	)
 
	was_unlocked = False
 
                          
	if user_achievement.progress >= user_achievement.achievement.target:
		user_achievement.is_completed = True
		user_achievement.unlocked_at = timezone.now()
		was_unlocked = True
  
                    
		award_xp_for_achievement(user, user_achievement.achievement)
 
	user_achievement.save()
	return user_achievement, was_unlocked


def award_xp_for_achievement(user, achievement: Achievement) -> UserXP:
\
\
\
\
\
    
	with transaction.atomic():
		user_xp, _ = UserXP.objects.get_or_create(
		 user=user,
		 defaults={'total_xp': 0, 'level': 1, 'current_level_xp': 0}
		)
		user_xp.add_xp(achievement.points)
  
                              
		_notify_achievement_unlock(user, achievement)
  
		return user_xp


def _notify_achievement_unlock(user, achievement: Achievement):
                                                        
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
                                                     
		import logging
		logger = logging.getLogger(__name__)
		logger.error(f"Failed to create achievement unlock notification: {e}")


                                                                              
                     
                                                                              

def track_review_streak(user) -> bool:
\
\
\
    
	return track_daily_activity_streak(user, 'review_streak_5', 5, 'reviews')


def track_listen_streak(user) -> bool:
\
\
\
    
	return track_daily_activity_streak(user, 'listen_streak_7', 7, 'listens')


def track_rating_streak(user) -> bool:
\
\
\
    
	return track_daily_activity_streak(user, 'rating_streak_3', 3, 'ratings')


def track_daily_activity_streak(user, achievement_code: str, target_days: int, activity_type: str) -> bool:
\
\
\
\
\
\
\
\
\
\
\
    
	user_achievement = get_or_create_achievement(user, achievement_code)
	if not user_achievement or user_achievement.is_completed:
		return False
 
                                       
	consecutive_days = count_consecutive_activity_days(user, activity_type)
 
                  
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
                                                     
	today = timezone.localdate()
	consecutive = 0
 
	for i in range(30):                          
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
			break                 
 
	return consecutive


                                                                              
                        
                                                                              

def track_review_milestone(user) -> bool:
\
\
\
    
	review_count = AlbumReview.objects.filter(user=user).count()
	user_achievement, was_unlocked = increment_achievement_progress(
	 user, 'reviewer_5', review_count
	)
	return was_unlocked


def track_rating_milestone(user) -> bool:
\
\
\
    
	rating_count = AlbumRating.objects.filter(user=user).count()
	user_achievement, was_unlocked = increment_achievement_progress(
	 user, 'rater_10', rating_count
	)
	return was_unlocked


def track_listen_milestone(user) -> bool:
\
\
\
    
	listen_count = AlbumListen.objects.filter(
	 user=user
	).values('album_id').distinct().count()
 
	user_achievement, was_unlocked = increment_achievement_progress(
	 user, 'listener_50', listen_count
	)
	return was_unlocked


def track_follow_milestone(user) -> bool:
\
\
\
    
	follow_count = ArtistFollow.objects.filter(user=user).count()
	user_achievement, was_unlocked = increment_achievement_progress(
	 user, 'fan_20', follow_count
	)
	return was_unlocked


                                                                              
                     
                                                                              

def track_liker_milestone(user) -> bool:
\
\
\
    
	like_count = AlbumLike.objects.filter(user=user).count()
	user_achievement, was_unlocked = increment_achievement_progress(
	 user, 'liker_25', like_count
	)
	return was_unlocked


def track_list_creator(user) -> bool:
\
\
\
    
	has_list = UserList.objects.filter(user=user).exists()
	if has_list:
		user_achievement, was_unlocked = increment_achievement_progress(
		 user, 'list_creator', 1
		)
		return was_unlocked
	return False


                                                                              
                        
                                                                              

def track_romanian_explorer(user) -> bool:
\
\
\
    
	from music.models import Artist
 
                                                                                
                                                                                                    
	listened_artists = Artist.objects.filter(
	 albums__listens__user=user
	).distinct().count()
 
	user_achievement, was_unlocked = increment_achievement_progress(
	 user, 'romanian_explorer', listened_artists
	)
	return was_unlocked


def track_genre_explorer(user) -> bool:
\
\
\
    
	genre_count = AlbumListen.objects.filter(
	 user=user
	).values('album__genres__id').distinct().count()
 
	user_achievement, was_unlocked = increment_achievement_progress(
	 user, 'genre_explorer', genre_count
	)
	return was_unlocked


def track_era_explorer(user) -> bool:
\
\
\
    
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


                                                                              
                                             
                                                                              

def update_all_achievement_progress(user):
\
\
\
    
	unlocked_achievements = []
 
                               
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
