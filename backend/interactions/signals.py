\
\
\
\
\
\
\
   

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)

from interactions.models import (
 AlbumReview,
 AlbumRating,
 AlbumLike,
 AlbumListen,
 ArtistFollow,
 List as UserList,
)
from interactions.achievement_tracker import (
 increment_achievement_progress,
 track_review_milestone,
 track_rating_milestone,
 track_listen_milestone,
 track_follow_milestone,
 track_liker_milestone,
 track_list_creator,
 track_romanian_explorer,
 track_genre_explorer,
 track_era_explorer,
 track_review_streak,
 track_listen_streak,
 track_rating_streak,
)


                                                                              
                
                                                                              

@receiver(post_save, sender=AlbumReview)
def on_album_review_created(sender, instance, created, **kwargs):
\
\
\
\
\
    
	if not created:
		return                          
 
	try:
		user = instance.user
  
                                  
		track_review_milestone(user)
		track_review_streak(user)
  
                                           
		from interactions.models import UserActivity
                                                                
		UserActivity.objects.create(
		 actor=user,
		 activity_type=UserActivity.Type.REVIEW_ALBUM,
		 target_id=(instance.album.id if instance.album else None),
		 target_name=(instance.title or (instance.album.title if instance.album else '')),
		)
  
		logger.info(f"✓ Review signal fired for user {user.id}: review_id={instance.id}")
	except Exception as e:
		logger.error(f"✗ Error in on_album_review_created signal: {str(e)}", exc_info=True)


                                                                              
                
                                                                              

@receiver(post_save, sender=AlbumRating)
def on_album_rating_created(sender, instance, created, **kwargs):
\
\
\
\
    
	if not created:
		return                          
 
	try:
		user = instance.user
  
                                  
		track_rating_milestone(user)
		track_rating_streak(user)
  
		logger.info(f"✓ Rating signal fired for user {user.id}: rating={instance.rating}")
	except Exception as e:
		logger.error(f"✗ Error in on_album_rating_created signal: {str(e)}", exc_info=True)


                                                                              
              
                                                                              

@receiver(post_save, sender=AlbumLike)
def on_album_liked(sender, instance, created, **kwargs):
\
\
\
    
	if not created:
		return                          
 
	try:
		user = instance.user
  
                                  
		track_liker_milestone(user)
  
		logger.info(f"✓ Like signal fired for user {user.id}: album_id={instance.album_id}")
	except Exception as e:
		logger.error(f"✗ Error in on_album_liked signal: {str(e)}", exc_info=True)


                                                                              
                
                                                                              

@receiver(post_save, sender=AlbumListen)
def on_album_listened(sender, instance, created, **kwargs):
\
\
\
\
\
\
\
    
	if not created:
		return                          
 
	try:
		user = instance.user
  
                                  
		track_listen_milestone(user)
		track_listen_streak(user)
		track_romanian_explorer(user)
		track_genre_explorer(user)
		track_era_explorer(user)
  
		logger.info(f"✓ Listen signal fired for user {user.id}: album_id={instance.album_id}")
	except Exception as e:
		logger.error(f"✗ Error in on_album_listened signal: {str(e)}", exc_info=True)


                                                                              
                
                                                                              

@receiver(post_save, sender=ArtistFollow)
def on_artist_followed(sender, instance, created, **kwargs):
\
\
\
    
	if not created:
		return                          
 
	try:
		user = instance.user
  
                                  
		track_follow_milestone(user)
  
		logger.info(f"✓ Follow signal fired for user {user.id}: artist_id={instance.artist_id}")
	except Exception as e:
		logger.error(f"✗ Error in on_artist_followed signal: {str(e)}", exc_info=True)


                                                                              
              
                                                                              

@receiver(post_save, sender=UserList)
def on_list_created(sender, instance, created, **kwargs):
\
\
\
    
	if not created:
		return                          
 
	try:
		user = instance.user
  
                                  
		track_list_creator(user)
  
		logger.info(f"✓ List signal fired for user {user.id}: list_id={instance.id}")
	except Exception as e:
		logger.error(f"✗ Error in on_list_created signal: {str(e)}", exc_info=True)
