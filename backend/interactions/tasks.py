"""
Celery tasks for gamification and periodic evaluations
"""
import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from config.celery import app
from interactions.achievement_tracker import award_xp_for_achievement
from interactions.models import AlbumRating, Achievement, UserActivity, AlbumLike, AlbumListen, FavoriteAlbum, AlbumReview
from interactions.recommender import compute_and_cache_neighbors, compute_and_cache_user_recommendations
from interactions.similarity import compute_and_cache_similar_users
from interactions.gamification import current_week_bounds, weekly_challenges_payload_for

logger = logging.getLogger(__name__)
User = get_user_model()


@app.task(bind=True, name='evaluate_weekly_challenges')
def evaluate_weekly_challenges(self):
	"""
	Evaluate weekly challenges for all users at the start of the week.
	Awards XP for completed challenges.
	Runs every Monday at 00:00 UTC.
	"""
	try:
		today = timezone.localdate()
		challenge_payload = {}
		
		# Get all active users
		users = User.objects.filter(is_active=True).select_related('userxp')
		
		completed_count = 0
		users_processed = 0
		
		for user in users:
			users_processed += 1
			try:
				# Get current week's challenges (which is the week that just ended)
				# This task runs on Monday, so "current" is already last week's challenges
				weekly_data = weekly_challenges_payload_for(user, today=today - timedelta(days=1))
				
				# Check for completed challenges
				if weekly_data.get('challenges'):
					for challenge in weekly_data.get('challenges', []):
						if challenge.get('completed'):
							challenge_key = challenge.get('key')
							
							# Award XP based on challenge completion
							xp_reward = 20  # Base XP for weekly challenge
							
							# Scale XP based on difficulty
							if challenge_key in ['listen_romanian_3', 'genres_3', 'rating_5', 'like_5']:
								xp_reward = 30
							elif challenge_key in ['review_2', 'create_list_1', 'follow_artist_2']:
								xp_reward = 25
							
							# Add XP to user
							try:
								from interactions.models import UserXP
								user_xp, _ = UserXP.objects.get_or_create(
									user=user,
									defaults={'total_xp': 0, 'level': 1, 'current_level_xp': 0}
								)
								user_xp.add_xp(xp_reward)
								completed_count += 1
								
								# Log activity
								UserActivity.objects.create(
									user=user,
									actor=user,
									activity_type=UserActivity.ActivityType.ACHIEVEMENT_UNLOCKED,
									target_type='weekly_challenge',
									target_id=challenge_key,
									summary=f'Completed weekly challenge: {challenge.get("title")} (+{xp_reward} XP)',
								)
							except Exception as e:
								logger.error(f"Error awarding XP to user {user.id} for challenge {challenge_key}: {e}")
				
				challenge_payload[str(user.id)] = weekly_data
			
			except Exception as e:
				logger.error(f"Error evaluating challenges for user {user.id}: {e}", exc_info=True)
		
		summary = f"Evaluated challenges for {users_processed} users, {completed_count} challenges completed, XP awarded"
		logger.info(summary)
		return {
			'status': 'success',
			'users_processed': users_processed,
			'challenges_completed': completed_count,
			'summary': summary,
		}
	
	except Exception as e:
		logger.error(f"Error in evaluate_weekly_challenges task: {e}", exc_info=True)
		return {
			'status': 'error',
			'error': str(e),
		}


@app.task(bind=True, name='reset_weekly_challenges')
def reset_weekly_challenges(self):
	"""
	Reset weekly challenges for all users at the start of the week.
	This is called after evaluate_weekly_challenges to prepare for the new week.
	
	Since weekly challenges are computed dynamically (not stored in DB),
	this task primarily serves as a trigger for any cached data resets
	or notifications to users about new challenges.
	"""
	try:
		# Reset any cached challenge data
		# (Implementation depends on caching strategy)
		
		users_notified = 0
		users = User.objects.filter(is_active=True)
		
		for user in users:
			try:
				# Get new week's challenges payload
				new_week_challenges = weekly_challenges_payload_for(user)
				
				# Could notify users about new challenges here
				# For now, just track that we processed them
				users_notified += 1
			
			except Exception as e:
				logger.error(f"Error resetting challenges for user {user.id}: {e}")
		
		summary = f"Reset weekly challenges for {users_notified} users. New challenges are now active."
		logger.info(summary)
		
		return {
			'status': 'success',
			'users_notified': users_notified,
			'summary': summary,
		}
	
	except Exception as e:
		logger.error(f"Error in reset_weekly_challenges task: {e}", exc_info=True)
		return {
			'status': 'error',
			'error': str(e),
		}


@app.task(bind=True, name='sync_achievement_progress')
def sync_achievement_progress(self, user_id: int):
	"""
	Sync achievement progress for a specific user.
	Can be called asynchronously from views when user activity is high.
	"""
	try:
		user = User.objects.get(id=user_id)
		
		from interactions.achievement_tracker import update_all_achievement_progress
		unlocked = update_all_achievement_progress(user)
		
		logger.info(f"Synced achievement progress for user {user_id}: {len(unlocked)} unlocked")
		
		return {
			'status': 'success',
			'user_id': user_id,
			'achievements_unlocked': unlocked,
		}
	
	except User.DoesNotExist:
		logger.error(f"User {user_id} not found")
		return {
			'status': 'error',
			'error': f'User {user_id} not found',
		}
	
	except Exception as e:
		logger.error(f"Error syncing achievement progress for user {user_id}: {e}", exc_info=True)
		return {
			'status': 'error',
			'error': str(e),
		}


@app.task(bind=True, name='precompute_recommendations')
def precompute_recommendations(self, limit: int = 12, max_users: int = 0):
	"""
	Precompute recommendation caches in the background.
	This mirrors the management command but is safe to enqueue from Celery beat
	or manual triggers when the cache needs refreshing outside the request cycle.
	"""
	try:
		user_ids = (
			AlbumRating.objects.values_list('user_id', flat=True)
			.distinct()
			.order_by()
		)
		if max_users and max_users > 0:
			user_ids = user_ids[:max_users]

		logger.info('Computing item neighbors before recommendation precompute')
		compute_and_cache_neighbors(k=50)

		users_processed = 0
		for user_id in user_ids:
			compute_and_cache_user_recommendations(int(user_id), limit=limit)
			users_processed += 1

		summary = (
			f'Precomputed recommendations for {users_processed} users '
			f'(limit={limit}, max_users={max_users or "all"})'
		)
		logger.info(summary)
		return {
			'status': 'success',
			'users_processed': users_processed,
			'limit': limit,
			'max_users': max_users,
			'summary': summary,
		}

	except Exception as e:
		logger.error(f'Error in precompute_recommendations task: {e}', exc_info=True)
		return {
			'status': 'error',
			'error': str(e),
		}


@app.task(bind=True, name='precompute_compatibility')
def precompute_compatibility(self, limit: int = 50, max_users: int = 0):
	"""
	Precompute user compatibility (similar users) caches in the background.
	Mirrors the management command `precompute_compatibility` but runs via Celery.
	"""
	try:
		user_ids = set()
		for model in (AlbumRating, AlbumLike, FavoriteAlbum, AlbumListen, AlbumReview):
			user_ids.update(model.objects.values_list('user_id', flat=True).distinct())
		ordered_user_ids = sorted(int(uid) for uid in user_ids if uid is not None)
		if max_users and max_users > 0:
			ordered_user_ids = ordered_user_ids[:max_users]

		users_processed = 0
		for uid in ordered_user_ids:
			compute_and_cache_similar_users(int(uid), limit=limit)
			users_processed += 1

		summary = (
			f'Precomputed compatibility for {users_processed} users '
			f'(limit={limit}, max_users={max_users or "all"})'
		)
		logger.info(summary)
		return {
			'status': 'success',
			'users_processed': users_processed,
			'limit': limit,
			'max_users': max_users,
			'summary': summary,
		}

	except Exception as e:
		logger.error(f'Error in precompute_compatibility task: {e}', exc_info=True)
		return {
			'status': 'error',
			'error': str(e),
		}
