from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from music.models import Album, Artist, Song


class AlbumRating(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='album_ratings')
	album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='ratings')
	rating = models.PositiveSmallIntegerField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('user', 'album')

	def __str__(self):
		return f"{self.user} - {self.album} ({self.rating})"


class SongRating(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='song_ratings')
	song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='ratings')
	rating = models.PositiveSmallIntegerField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('user', 'song')

	def __str__(self):
		return f"{self.user} - {self.song} ({self.rating})"


class AlbumReview(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='album_reviews')
	album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='reviews')
	title = models.CharField(max_length=255, blank=True)
	content = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"Review by {self.user} for {self.album}"


class AlbumReviewLike(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='album_review_likes',
	)
	review = models.ForeignKey(
		AlbumReview,
		on_delete=models.CASCADE,
		related_name='likes',
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('user', 'review')

	def __str__(self):
		return f"{self.user} likes review {self.review_id}"


class AlbumReviewReaction(models.Model):
	"""Emoji reaction on an album review"""
	EMOJI_CHOICES = [
		('👍', '👍 Thumbs Up'),
		('❤️', '❤️ Heart'),
		('😂', '😂 Laughing'),
		('😮', '😮 Surprised'),
		('😢', '😢 Sad'),
		('🔥', '🔥 Fire'),
		('👏', '👏 Clapping'),
		('🎉', '🎉 Party'),
	]

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='album_review_reactions',
	)
	review = models.ForeignKey(
		AlbumReview,
		on_delete=models.CASCADE,
		related_name='reactions',
	)
	emoji = models.CharField(max_length=10, choices=EMOJI_CHOICES)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('user', 'review', 'emoji')
		ordering = ['created_at']
		indexes = [
			models.Index(fields=['review', 'emoji']),
			models.Index(fields=['user', '-created_at']),
		]

	def __str__(self):
		return f"{self.user} reacted {self.emoji} to review {self.review_id}"


class ReviewComment(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='review_comments',
	)
	review = models.ForeignKey(
		AlbumReview,
		on_delete=models.CASCADE,
		related_name='comments',
	)
	parent = models.ForeignKey(
		'self',
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name='replies',
	)
	content = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['created_at']
		indexes = [
			models.Index(fields=['review', 'created_at']),
			models.Index(fields=['parent', 'created_at']),
			models.Index(fields=['user', 'created_at']),
		]

	def __str__(self):
		return f"Comment by {self.user_id} on review {self.review_id}"


class ReviewCommentMention(models.Model):
	comment = models.ForeignKey(
		ReviewComment,
		on_delete=models.CASCADE,
		related_name='mentions',
	)
	mentioned_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='review_comment_mentions',
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		constraints = [
			models.UniqueConstraint(
				fields=['comment', 'mentioned_user'],
				name='unique_review_comment_mention',
			),
		]
		indexes = [
			models.Index(fields=['mentioned_user', '-created_at']),
			models.Index(fields=['comment', '-created_at']),
		]

	def __str__(self):
		return f"mention {self.mentioned_user_id} in comment {self.comment_id}"


class ReviewCommentEdit(models.Model):
	comment = models.ForeignKey(
		ReviewComment,
		on_delete=models.CASCADE,
		related_name='edits',
	)
	edited_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='review_comment_edits',
	)
	previous_content = models.TextField(blank=True, default='')
	edited_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-edited_at', '-id']
		indexes = [
			models.Index(fields=['comment', '-edited_at']),
		]

	def __str__(self) -> str:
		return f"comment_edit:{self.comment_id} @ {self.edited_at}"


class SongComment(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='song_comments',
	)
	song = models.ForeignKey(
		Song,
		on_delete=models.CASCADE,
		related_name='comments',
	)
	parent = models.ForeignKey(
		'self',
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name='replies',
	)
	content = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['created_at']
		indexes = [
			models.Index(fields=['song', 'created_at']),
			models.Index(fields=['parent', 'created_at']),
			models.Index(fields=['user', 'created_at']),
		]

	def __str__(self):
		return f"Comment by {self.user_id} on song {self.song_id}"


class SongCommentMention(models.Model):
	comment = models.ForeignKey(
		SongComment,
		on_delete=models.CASCADE,
		related_name='mentions',
	)
	mentioned_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='song_comment_mentions',
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		constraints = [
			models.UniqueConstraint(
				fields=['comment', 'mentioned_user'],
				name='unique_song_comment_mention',
			),
		]
		indexes = [
			models.Index(fields=['mentioned_user', '-created_at']),
			models.Index(fields=['comment', '-created_at']),
		]

	def __str__(self):
		return f"mention {self.mentioned_user_id} in song comment {self.comment_id}"


class SongCommentEdit(models.Model):
	comment = models.ForeignKey(
		SongComment,
		on_delete=models.CASCADE,
		related_name='edits',
	)
	edited_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='song_comment_edits',
	)
	previous_content = models.TextField(blank=True, default='')
	edited_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-edited_at', '-id']
		indexes = [
			models.Index(fields=['comment', '-edited_at']),
		]

	def __str__(self) -> str:
		return f"song_comment_edit:{self.comment_id} @ {self.edited_at}"


class FavoriteAlbum(models.Model):
	class Position(models.IntegerChoices):
		ONE = 1, '1'
		TWO = 2, '2'
		THREE = 3, '3'
		FOUR = 4, '4'

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='favorite_albums',
	)
	album = models.ForeignKey(
		Album,
		on_delete=models.CASCADE,
		related_name='favorited_by',
	)
	position = models.PositiveSmallIntegerField(choices=Position.choices)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['user', 'position'], name='unique_favorite_album_position_per_user'),
			models.UniqueConstraint(fields=['user', 'album'], name='unique_favorite_album_per_user'),
		]
		ordering = ['position', 'id']
		indexes = [
			models.Index(fields=['user', 'position']),
		]

	def __str__(self):
		return f"{self.user_id} favorite {self.album_id} @ {self.position}"


class FavoriteSong(models.Model):
	class Position(models.IntegerChoices):
		ONE = 1, '1'
		TWO = 2, '2'
		THREE = 3, '3'
		FOUR = 4, '4'

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='favorite_songs',
	)
	song = models.ForeignKey(
		Song,
		on_delete=models.CASCADE,
		related_name='favorited_by',
	)
	position = models.PositiveSmallIntegerField(choices=Position.choices)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['user', 'position'], name='unique_favorite_song_position_per_user'),
			models.UniqueConstraint(fields=['user', 'song'], name='unique_favorite_song_per_user'),
		]
		ordering = ['position', 'id']
		indexes = [
			models.Index(fields=['user', 'position']),
		]

	def __str__(self):
		return f"{self.user_id} favorite song {self.song_id} @ {self.position}"


class AlbumListen(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='album_listens',
	)
	album = models.ForeignKey(
		Album,
		on_delete=models.CASCADE,
		related_name='listens',
	)
	listened_at = models.DateTimeField(auto_now_add=True)
	# Used to enforce 1 listen/day/user/album and to query by date cheaply.
	listened_date = models.DateField(default=timezone.localdate, db_index=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=['user', 'album', 'listened_date'],
				name='unique_album_listen_per_day',
			),
		]
		ordering = ['-listened_at']
		indexes = [
			models.Index(fields=['album', '-listened_at']),
			models.Index(fields=['user', '-listened_at']),
		]

	def __str__(self):
		return f"{self.user_id} listened {self.album_id} on {self.listened_date}"


class WantToListen(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='want_to_listen',
	)
	album = models.ForeignKey(
		Album,
		on_delete=models.CASCADE,
		related_name='wanted_by',
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=['user', 'album'],
				name='unique_want_to_listen_per_user_album',
			),
		]
		ordering = ['-created_at', '-id']
		indexes = [
			models.Index(fields=['user', '-created_at'], name='w2l_user_created_idx'),
			models.Index(fields=['album', '-created_at'], name='w2l_album_created_idx'),
		]

	def __str__(self):
		return f"{self.user_id} wants {self.album_id}"


class AlbumLike(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='album_likes',
	)
	album = models.ForeignKey(
		Album,
		on_delete=models.CASCADE,
		related_name='liked_by',
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=['user', 'album'],
				name='unique_album_like_per_user_album',
			),
		]
		ordering = ['-created_at', '-id']
		indexes = [
			models.Index(fields=['user', '-created_at'], name='al_user_created_idx'),
			models.Index(fields=['album', '-created_at'], name='al_album_created_idx'),
		]

	def __str__(self):
		return f"{self.user_id} likes {self.album_id}"


class SongLike(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='song_likes',
	)
	song = models.ForeignKey(
		Song,
		on_delete=models.CASCADE,
		related_name='liked_by',
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=['user', 'song'],
				name='unique_song_like_per_user_song',
			),
		]
		ordering = ['-created_at', '-id']
		indexes = [
			models.Index(fields=['user', '-created_at'], name='sl_user_created_idx'),
			models.Index(fields=['song', '-created_at'], name='sl_song_created_idx'),
		]

	def __str__(self):
		return f"{self.user_id} likes {self.song_id}"


class List(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='lists',
	)
	name = models.CharField(max_length=255)
	description = models.TextField(blank=True, default='')
	is_public = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	albums = models.ManyToManyField(
		Album,
		through='ListAlbum',
		related_name='in_lists',
		blank=True,
	)

	tags = models.ManyToManyField(
		'ListTag',
		related_name='lists',
		blank=True,
	)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['user', 'name'], name='unique_list_name_per_user'),
		]
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.user} - {self.name}"


class ListLike(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='list_likes',
	)
	list = models.ForeignKey(
		List,
		on_delete=models.CASCADE,
		related_name='likes',
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['user', 'list'], name='unique_list_like'),
		]
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['list', '-created_at']),
			models.Index(fields=['user', '-created_at']),
		]

	def __str__(self):
		return f"{self.user_id} likes {self.list_id}"


class ListAlbum(models.Model):
	list = models.ForeignKey(List, on_delete=models.CASCADE, related_name='list_albums')
	album = models.ForeignKey(Album, on_delete=models.CASCADE, related_name='list_albums')
	position = models.PositiveIntegerField(default=0, db_index=True)
	added_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('list', 'album')
		ordering = ['position', 'id']

	def __str__(self):
		return f"{self.list_id} -> {self.album_id}"


class ListMembership(models.Model):
	class Role(models.TextChoices):
		OWNER = 'owner', 'Owner'
		EDITOR = 'editor', 'Editor'

	list = models.ForeignKey(List, on_delete=models.CASCADE, related_name='memberships')
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='list_memberships',
	)
	role = models.CharField(max_length=20, choices=Role.choices, default=Role.EDITOR)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['list', 'user'], name='unique_list_membership'),
		]
		indexes = [
			models.Index(fields=['user', 'role']),
			models.Index(fields=['list', 'role']),
		]

	def __str__(self):
		return f"{self.user_id} in {self.list_id} ({self.role})"


class ListTag(models.Model):
	owner = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='list_tags',
	)
	name = models.CharField(max_length=50)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['owner', 'name'], name='unique_list_tag_per_owner'),
		]
		ordering = ['name', 'id']
		indexes = [
			models.Index(fields=['owner', 'name']),
		]

	def __str__(self):
		return f"{self.owner_id}:{self.name}"


class ListAlbumNote(models.Model):
	list_album = models.ForeignKey(
		ListAlbum,
		on_delete=models.CASCADE,
		related_name='notes',
	)
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='list_album_notes',
	)
	note = models.TextField(blank=True, default='')
	updated_at = models.DateTimeField(auto_now=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['list_album', 'user'], name='unique_list_album_note'),
		]
		indexes = [
			models.Index(fields=['user', '-updated_at']),
			models.Index(fields=['list_album', '-updated_at']),
		]

	def __str__(self):
		return f"note:{self.user_id} on item {self.list_album_id}"


class AlbumReviewEdit(models.Model):
	review = models.ForeignKey(
		AlbumReview,
		on_delete=models.CASCADE,
		related_name='edits',
	)
	edited_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='album_review_edits',
	)
	previous_title = models.CharField(max_length=255, blank=True)
	previous_content = models.TextField(blank=True)
	edited_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-edited_at', '-id']
		indexes = [
			models.Index(fields=['review', '-edited_at']),
		]

	def __str__(self):
		return f"edit:{self.review_id} @ {self.edited_at}"


class AlbumReviewDraft(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='album_review_drafts',
	)
	album = models.ForeignKey(
		Album,
		on_delete=models.CASCADE,
		related_name='review_drafts',
	)
	title = models.CharField(max_length=255, blank=True, default='')
	content = models.TextField(blank=True, default='')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['user', 'album'], name='unique_review_draft_per_user_album'),
		]
		indexes = [
			models.Index(fields=['user', '-updated_at']),
			models.Index(fields=['album', '-updated_at']),
		]

	def __str__(self):
		return f"draft:{self.user_id}:{self.album_id}"


class ModerationReport(models.Model):
	class ReasonCode(models.TextChoices):
		SPAM = 'spam', 'Spam'
		ABUSE = 'abuse', 'Abuse'
		DUPLICATE = 'duplicate', 'Duplicate'
		OTHER = 'other', 'Other'

	class Status(models.TextChoices):
		PENDING = 'pending', 'Pending'
		RESOLVED = 'resolved', 'Resolved'

	reporter = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='moderation_reports',
	)
	review = models.ForeignKey(
		AlbumReview,
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name='reports',
	)
	review_comment = models.ForeignKey(
		ReviewComment,
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name='reports',
	)
	song_comment = models.ForeignKey(
		SongComment,
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name='reports',
	)
	reason_code = models.CharField(max_length=20, choices=ReasonCode.choices, default=ReasonCode.OTHER)
	reason = models.TextField(blank=True, default='')
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	created_at = models.DateTimeField(auto_now_add=True)
	resolved_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='resolved_moderation_reports',
	)
	resolved_at = models.DateTimeField(null=True, blank=True)
	resolution_reason = models.CharField(max_length=255, blank=True, default='')
	resolution_feedback = models.TextField(blank=True, default='')

	class Meta:
		ordering = ['-created_at', '-id']
		constraints = [
			models.CheckConstraint(
				name='moderation_report_has_target',
				condition=(
					Q(review__isnull=False)
					| Q(review_comment__isnull=False)
					| Q(song_comment__isnull=False)
				),
			),
			models.CheckConstraint(
				name='moderation_report_one_target_only',
				condition=(
					~(Q(review__isnull=False) & Q(review_comment__isnull=False))
					& ~(Q(review__isnull=False) & Q(song_comment__isnull=False))
					& ~(Q(review_comment__isnull=False) & Q(song_comment__isnull=False))
				),
			),
		]
		indexes = [
			models.Index(fields=['status', '-created_at']),
			models.Index(fields=['reason_code', 'status', '-created_at']),
			models.Index(fields=['reporter', '-created_at']),
		]

	def __str__(self):
		return f"report:{self.id} ({self.status})"


class UserSuspension(models.Model):
	"""Track user suspensions/bans due to moderation"""
	class SuspensionReason(models.TextChoices):
		CONTENT_VIOLATION = 'content_violation', 'Content Violation'
		SPAM = 'spam', 'Spam'
		ABUSE = 'abuse', 'Abuse'
		HARASSMENT = 'harassment', 'Harassment'
		FALSE_INFO = 'false_info', 'False Information'
		OTHER = 'other', 'Other'

	class SuspensionDuration(models.TextChoices):
		PERMANENT = 'permanent', 'Permanent'
		ONE_WEEK = 'one_week', '1 Week'
		ONE_MONTH = 'one_month', '1 Month'
		THREE_MONTHS = 'three_months', '3 Months'
		CUSTOM = 'custom', 'Custom'

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='suspensions',
	)
	reason = models.CharField(
		max_length=50,
		choices=SuspensionReason.choices,
		default=SuspensionReason.OTHER,
	)
	duration_type = models.CharField(
		max_length=20,
		choices=SuspensionDuration.choices,
		default=SuspensionDuration.ONE_MONTH,
	)
	suspended_at = models.DateTimeField(auto_now_add=True)
	suspended_until = models.DateTimeField(null=True, blank=True)
	reason_detail = models.TextField(blank=True)
	suspended_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='suspensions_issued',
	)
	related_report = models.ForeignKey(
		ModerationReport,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='suspensions',
	)
	is_active = models.BooleanField(default=True)
	appeal_at = models.DateTimeField(null=True, blank=True)
	appeal_reason = models.TextField(blank=True)
	appealed_by_user = models.BooleanField(default=False)

	class Meta:
		ordering = ['-suspended_at', '-id']
		indexes = [
			models.Index(fields=['user', '-suspended_at']),
			models.Index(fields=['is_active', '-suspended_at']),
		]

	def __str__(self):
		return f"{self.user} suspended until {self.suspended_until or 'permanent'}"

	@property
	def is_expired(self):
		"""Check if suspension has expired"""
		if self.suspended_until and timezone.now() > self.suspended_until:
			return True
		return False


class ArtistFollow(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='artist_follows',
	)
	artist = models.ForeignKey(
		Artist,
		on_delete=models.CASCADE,
		related_name='followers',
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('user', 'artist')
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.user} follows {self.artist}"


class FriendRequest(models.Model):
	class Status(models.TextChoices):
		PENDING = 'pending', 'Pending'
		ACCEPTED = 'accepted', 'Accepted'
		REJECTED = 'rejected', 'Rejected'

	sender = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='sent_friend_requests',
	)
	receiver = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='received_friend_requests',
	)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['sender', 'receiver'], name='unique_friend_request_pair'),
		]
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.sender_id} -> {self.receiver_id} ({self.status})"


class UserActivity(models.Model):
	class Type(models.TextChoices):
		LISTEN_ALBUM = 'listen_album', 'Listen album'
		RATE_ALBUM = 'rate_album', 'Rate album'
		REVIEW_ALBUM = 'review_album', 'Review album'
		FOLLOW_ARTIST = 'follow_artist', 'Follow artist'
		CREATE_LIST = 'create_list', 'Create list'
		LIST_ADD_ALBUM = 'list_add_album', 'Add album to list'

	actor = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='activities',
	)
	activity_type = models.CharField(max_length=30, choices=Type.choices)
	# Minimal denormalized target info so we can render the feed cheaply.
	target_id = models.IntegerField(null=True, blank=True)
	target_name = models.CharField(max_length=255, blank=True)
	rating = models.PositiveSmallIntegerField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['-created_at']),
			models.Index(fields=['actor', '-created_at']),
			models.Index(fields=['activity_type', '-created_at']),
		]

	def __str__(self):
		return f"{self.actor_id} {self.activity_type} {self.target_name}"


class SensitiveActionAudit(models.Model):
	class ActionType(models.TextChoices):
		REPORT_CREATED = 'report_created', 'Report created'
		REPORT_RESOLVED = 'report_resolved', 'Report resolved'
		COMMENT_CREATED = 'comment_created', 'Comment created'
		COMMENT_EDITED = 'comment_edited', 'Comment edited'
		DM_SENT = 'dm_sent', 'DM sent'
		METADATA_SUGGESTION_CREATED = 'metadata_suggestion_created', 'Metadata suggestion created'
		METADATA_SUGGESTION_DECIDED = 'metadata_suggestion_decided', 'Metadata suggestion decided'

	actor = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='sensitive_action_audits',
	)
	action_type = models.CharField(max_length=48, choices=ActionType.choices)
	target_type = models.CharField(max_length=64)
	target_id = models.IntegerField(null=True, blank=True)
	summary = models.CharField(max_length=255, blank=True, default='')
	metadata = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at', '-id']
		indexes = [
			models.Index(fields=['-created_at']),
			models.Index(fields=['actor', '-created_at']),
			models.Index(fields=['action_type', '-created_at']),
			models.Index(fields=['target_type', 'target_id']),
		]

	def __str__(self):
		return f"audit:{self.id}:{self.action_type}:{self.target_type}:{self.target_id}"


class AnalyticsEvent(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='analytics_events',
	)
	event_name = models.CharField(max_length=64)
	target_type = models.CharField(max_length=64, blank=True, default='')
	target_id = models.IntegerField(null=True, blank=True)
	properties = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at', '-id']
		indexes = [
			models.Index(fields=['-created_at']),
			models.Index(fields=['user', '-created_at']),
			models.Index(fields=['event_name', '-created_at']),
			models.Index(fields=['target_type', 'target_id']),
		]

	def __str__(self):
		return f"event:{self.id}:{self.event_name}:{self.user_id}"


class NotificationPreferences(models.Model):
	class DigestFrequency(models.TextChoices):
		OFF = 'off', 'Off'
		DAILY = 'daily', 'Daily'
		WEEKLY = 'weekly', 'Weekly'

	class DigestChannel(models.TextChoices):
		IN_APP = 'in_app', 'In-app'
		EMAIL = 'email', 'Email'

	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='notification_preferences',
	)

	# Notification categories
	notify_friend_requests = models.BooleanField(default=True)
	notify_review_likes = models.BooleanField(default=True)
	notify_review_replies = models.BooleanField(default=True)
	notify_mentions = models.BooleanField(default=True)
	notify_artist_follows = models.BooleanField(default=True)
	notify_followed_artist_releases = models.BooleanField(default=True)
	notify_genre_releases = models.BooleanField(default=True)
	notify_release_reminders = models.BooleanField(default=True)
	release_reminder_days = models.PositiveSmallIntegerField(default=3)
	notify_achievement_unlocks = models.BooleanField(default=True)

	# Digest categories
	notify_friends_activity = models.BooleanField(default=True)

	# Digest scheduling (used for in-app summary; email delivery can be added later)
	digest_frequency = models.CharField(
		max_length=10,
		choices=DigestFrequency.choices,
		default=DigestFrequency.OFF,
	)
	digest_channel = models.CharField(
		max_length=10,
		choices=DigestChannel.choices,
		default=DigestChannel.IN_APP,
	)

	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"notif_prefs {self.user_id}"


class ChatMessage(models.Model):
	sender = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='sent_messages',
	)
	recipient = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='received_messages',
	)
	reply_to = models.ForeignKey(
		'self',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='replies',
	)
	content = models.TextField()
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']
		indexes = [
			models.Index(fields=['sender', 'recipient', '-created_at']),
			models.Index(fields=['recipient', 'is_read']),
			models.Index(fields=['reply_to']),
		]

	def __str__(self):
		preview = (self.content or '').replace('\n', ' ').strip()
		preview = preview[:30] + ('…' if len(preview) > 30 else '')
		return f"{self.sender_id} → {self.recipient_id}: {preview}"


class ChatTypingStatus(models.Model):
	"""Tracks temporary typing state between two users in DMs."""
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='typing_statuses',
	)
	partner = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='typing_statuses_for_partner',
	)
	is_typing = models.BooleanField(default=False)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=['user', 'partner'],
				name='unique_typing_status_per_pair',
			),
		]
		indexes = [
			models.Index(fields=['partner', 'is_typing', '-updated_at']),
			models.Index(fields=['user', 'partner']),
		]

	def __str__(self):
		return f"typing:{self.user_id}->{self.partner_id}:{self.is_typing}"


class UserOnboarding(models.Model):
	"""Track user's first-time onboarding: genre/artist preferences."""
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='onboarding',
	)
	is_completed = models.BooleanField(default=False)
	preferred_genres = models.ManyToManyField(
		'music.Genre',
		blank=True,
		related_name='onboarded_users',
	)
	preferred_artists = models.ManyToManyField(
		Artist,
		blank=True,
		related_name='onboarded_users',
	)
	completed_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'User onboarding'
		verbose_name_plural = 'User onboarding'

	def __str__(self):
		return f"onboarding:{self.user_id}:{self.is_completed}"


class CorrectionReport(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='correction_reports',
	)
	page_url = models.CharField(max_length=500, blank=True)
	description = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at', '-id']
		indexes = [
			models.Index(fields=['-created_at']),
			models.Index(fields=['user', '-created_at']),
		]

	def __str__(self):
		preview = (self.description or '').replace('\n', ' ').strip()
		preview = preview[:30] + ('…' if len(preview) > 30 else '')
		return f"correction {self.id}: {preview}"


class MetadataSuggestion(models.Model):
	"""Crowdsourced metadata corrections with an approval flow.

	Targets only approved catalog entries (artist/album/song). Moderators can
	approve/reject suggestions; approval may optionally apply changes.
	"""

	class Kind(models.TextChoices):
		RELEASE_DATE = 'release_date', 'Release date'
		COVER_URL = 'cover_url', 'Cover URL'
		IMAGE_URL = 'image_url', 'Artist image'
		TRACKLIST = 'tracklist', 'Tracklist'
		BIO = 'bio', 'Bio'
		ALIASES = 'aliases', 'Aliases'
		DESCRIPTION = 'description', 'Description'
		OTHER = 'other', 'Other'

	class Status(models.TextChoices):
		PENDING = 'pending', 'Pending'
		APPROVED = 'approved', 'Approved'
		REJECTED = 'rejected', 'Rejected'

	suggester = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='metadata_suggestions',
	)
	artist = models.ForeignKey(
		Artist,
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name='metadata_suggestions',
	)
	album = models.ForeignKey(
		Album,
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name='metadata_suggestions',
	)
	song = models.ForeignKey(
		Song,
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name='metadata_suggestions',
	)
	kind = models.CharField(max_length=32, choices=Kind.choices)
	# Suggested content; schema depends on `kind`.
	payload = models.JSONField(default=dict, blank=True)
	note = models.TextField(blank=True, default='')
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	created_at = models.DateTimeField(auto_now_add=True)
	reviewed_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='reviewed_metadata_suggestions',
	)
	reviewed_at = models.DateTimeField(null=True, blank=True)
	decision_note = models.TextField(blank=True, default='')
	# When approved, whether changes were applied automatically.
	applied = models.BooleanField(default=False)

	class Meta:
		ordering = ['-created_at', '-id']
		constraints = [
			models.CheckConstraint(
				name='metadata_suggestion_has_target',
				condition=(
					Q(artist__isnull=False)
					| Q(album__isnull=False)
					| Q(song__isnull=False)
				),
			),
			models.CheckConstraint(
				name='metadata_suggestion_one_target_only',
				condition=(
					~(Q(artist__isnull=False) & Q(album__isnull=False))
					& ~(Q(artist__isnull=False) & Q(song__isnull=False))
					& ~(Q(album__isnull=False) & Q(song__isnull=False))
				),
			),
		]
		indexes = [
			models.Index(fields=['status', '-created_at']),
			models.Index(fields=['kind', 'status', '-created_at']),
			models.Index(fields=['suggester', '-created_at']),
		]

	def __str__(self) -> str:
		return f"meta_suggestion:{self.id} ({self.kind},{self.status})"


class CatalogChangelogEvent(models.Model):
	"""Public changelog entry for an approved catalog item.

	Created when a MetadataSuggestion is applied (or by staff manually later).
	"""

	actor = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='catalog_changelog_events',
	)
	suggestion = models.ForeignKey(
		MetadataSuggestion,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='changelog_events',
	)
	artist = models.ForeignKey(
		Artist,
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name='changelog_events',
	)
	album = models.ForeignKey(
		Album,
		on_delete=models.CASCADE,
		null=True,
		blank=True,
		related_name='changelog_events',
	)
	kind = models.CharField(max_length=32, blank=True, default='')
	summary = models.CharField(max_length=255)
	diff = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at', '-id']
		constraints = [
			models.CheckConstraint(
				name='changelog_event_has_target',
				condition=(Q(artist__isnull=False) | Q(album__isnull=False)),
			),
			models.CheckConstraint(
				name='changelog_event_one_target_only',
				condition=(~(Q(artist__isnull=False) & Q(album__isnull=False))),
			),
		]
		indexes = [
			models.Index(fields=['artist', '-created_at']),
			models.Index(fields=['album', '-created_at']),
			models.Index(fields=['kind', '-created_at']),
		]

	def __str__(self) -> str:
		who = getattr(self.actor, 'username', None) or 'staff'
		return f"changelog ({who}): {self.summary}"


class ReviewCommentReaction(models.Model):
	"""Emoji reaction on a review comment"""
	EMOJI_CHOICES = [
		('👍', '👍 Thumbs Up'),
		('❤️', '❤️ Heart'),
		('😂', '😂 Laughing'),
		('😮', '😮 Surprised'),
		('😢', '😢 Sad'),
		('🔥', '🔥 Fire'),
		('👏', '👏 Clapping'),
		('🎉', '🎉 Party'),
	]

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='review_comment_reactions',
	)
	comment = models.ForeignKey(
		ReviewComment,
		on_delete=models.CASCADE,
		related_name='reactions',
	)
	emoji = models.CharField(max_length=10, choices=EMOJI_CHOICES)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('user', 'comment', 'emoji')
		ordering = ['created_at']
		indexes = [
			models.Index(fields=['comment', 'emoji']),
			models.Index(fields=['user', '-created_at']),
		]

	def __str__(self):
		return f"{self.user} reacted {self.emoji} to comment {self.comment_id}"


class SongCommentReaction(models.Model):
	"""Emoji reaction on a song comment"""
	EMOJI_CHOICES = [
		('👍', '👍 Thumbs Up'),
		('❤️', '❤️ Heart'),
		('😂', '😂 Laughing'),
		('😮', '😮 Surprised'),
		('😢', '😢 Sad'),
		('🔥', '🔥 Fire'),
		('👏', '👏 Clapping'),
		('🎉', '🎉 Party'),
	]

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='song_comment_reactions',
	)
	comment = models.ForeignKey(
		SongComment,
		on_delete=models.CASCADE,
		related_name='reactions',
	)
	emoji = models.CharField(max_length=10, choices=EMOJI_CHOICES)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		unique_together = ('user', 'comment', 'emoji')
		ordering = ['created_at']
		indexes = [
			models.Index(fields=['comment', 'emoji']),
			models.Index(fields=['user', '-created_at']),
		]

	def __str__(self):
		return f"{self.user} reacted {self.emoji} to comment {self.comment_id}"


# ============= GAMIFICATION: BADGES & ACHIEVEMENTS =============


class AchievementUnlock(models.Model):
	"""Track when achievements are unlocked for notifications"""
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='achievement_unlocks',
	)
	achievement = models.ForeignKey(
		'Achievement',
		on_delete=models.CASCADE,
		null=True,
		blank=True,
	)
	achievement_code = models.CharField(max_length=64)
	achievement_name = models.CharField(max_length=256, blank=True)
	achievement_emoji = models.CharField(max_length=10, blank=True)
	xp_awarded = models.IntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at', '-id']
		indexes = [
			models.Index(fields=['user', '-created_at']),
			models.Index(fields=['-created_at']),
		]

	def __str__(self):
		return f"{self.user} unlocked {self.achievement_code} on {self.created_at}"


class Badge(models.Model):
	"""Badge definition - a type of badge that can be earned"""
	class Category(models.TextChoices):
		MUSIC_EXPLORER = 'explorer', 'Music Explorer'
		CRITIC = 'critic', 'Critic'
		SOCIAL = 'social', 'Social Butterfly'
		ACTIVITY = 'activity', 'Activity Tracker'
		COLLECTOR = 'collector', 'Collector'
		MILESTONE = 'milestone', 'Milestone'

	code = models.CharField(max_length=50, unique=True, db_index=True)  # e.g., "first_review", "100_ratings"
	name = models.CharField(max_length=100)
	description = models.TextField()
	emoji = models.CharField(max_length=10, default='🏆')
	category = models.CharField(max_length=20, choices=Category.choices)
	rarity = models.CharField(
		max_length=10,
		choices=[
			('common', 'Common'),
			('uncommon', 'Uncommon'),
			('rare', 'Rare'),
			('epic', 'Epic'),
			('legendary', 'Legendary'),
		],
		default='common',
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['category', 'name']
		indexes = [
			models.Index(fields=['code']),
			models.Index(fields=['category']),
		]

	def __str__(self):
		return f"{self.emoji} {self.name}"


class UserBadge(models.Model):
	"""Track which badges a user has earned"""
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='badges_earned',
	)
	badge = models.ForeignKey(
		Badge,
		on_delete=models.CASCADE,
		related_name='earned_by',
	)
	earned_at = models.DateTimeField(auto_now_add=True)
	progress = models.PositiveIntegerField(default=0)  # e.g., current rating count for "100_ratings"
	target = models.PositiveIntegerField(default=0)  # e.g., 100 for "100_ratings"

	class Meta:
		unique_together = ('user', 'badge')
		ordering = ['-earned_at']
		indexes = [
			models.Index(fields=['user', '-earned_at']),
			models.Index(fields=['badge', '-earned_at']),
		]

	def __str__(self):
		return f"{self.user.username} earned {self.badge.name}"


class Achievement(models.Model):
	"""Achievement definition - a long-term goal/milestone"""
	class Type(models.TextChoices):
		STREAK = 'streak', 'Streak Achievement'
		MILESTONE = 'milestone', 'Milestone Achievement'
		SOCIAL = 'social', 'Social Achievement'
		DISCOVERY = 'discovery', 'Discovery Achievement'

	code = models.CharField(max_length=50, unique=True, db_index=True)
	name = models.CharField(max_length=100)
	description = models.TextField()
	emoji = models.CharField(max_length=10, default='⭐')
	type = models.CharField(max_length=20, choices=Type.choices)
	target = models.PositiveIntegerField()  # e.g., 7 for "7_day_streak"
	points = models.PositiveIntegerField(default=10)  # XP points awarded
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['type', 'name']
		indexes = [
			models.Index(fields=['code']),
			models.Index(fields=['type']),
		]

	def __str__(self):
		return f"{self.emoji} {self.name}"


class UserAchievement(models.Model):
	"""Track which achievements a user has unlocked"""
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='achievements_unlocked',
	)
	achievement = models.ForeignKey(
		Achievement,
		on_delete=models.CASCADE,
		related_name='unlocked_by',
	)
	progress = models.PositiveIntegerField(default=0)  # e.g., current streak days
	unlocked_at = models.DateTimeField(null=True, blank=True)
	is_completed = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = ('user', 'achievement')
		ordering = ['-unlocked_at', '-updated_at']
		indexes = [
			models.Index(fields=['user', 'is_completed']),
			models.Index(fields=['achievement', 'is_completed']),
			models.Index(fields=['user', '-unlocked_at']),
		]

	def __str__(self):
		status = "✓" if self.is_completed else "○"
		return f"{status} {self.user.username} - {self.achievement.name}"


class UserXP(models.Model):
	"""Track total XP earned by user from achievements and badges"""
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name='user_xp',
	)
	total_xp = models.PositiveIntegerField(default=0)
	level = models.PositiveIntegerField(default=1)
	current_level_xp = models.PositiveIntegerField(default=0)
	last_updated = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = 'User XP'
		verbose_name_plural = 'User XP'

	def __str__(self):
		return f"{self.user.username} - Level {self.level} ({self.total_xp} XP)"

	@staticmethod
	def xp_for_level(level):
		"""Calculate XP needed to reach a level"""
		return (level - 1) * 500 + 500  # 500 XP for level 1, then +500 per level

	def add_xp(self, amount):
		"""Add XP and handle level up"""
		self.total_xp += amount
		self.current_level_xp += amount

		# Check for level ups
		while self.current_level_xp >= self.xp_for_level(self.level + 1):
			self.current_level_xp -= self.xp_for_level(self.level + 1)
			self.level += 1

		self.save()
