import json
from datetime import date
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from music.models import Album, Artist, Song
from interactions.gamification import weekly_challenges_payload_for
from interactions.tasks import precompute_recommendations, precompute_compatibility
from interactions.models import (
	AlbumLike,
	AlbumListen,
	AlbumRating,
	AlbumReview,
	AlbumReviewLike,
	ArtistFollow,
	ChatMessage,
	CorrectionReport,
	FavoriteAlbum,
	FavoriteSong,
	FriendRequest,
	List,
	ListAlbum,
	ReviewComment,
	SongComment,
	SongLike,
	SongRating,
	UserActivity,
	WantToListen,
)

from music.models import Genre


class TestFullMainFlows(TestCase):
	def setUp(self):
		self.client = APIClient()

		self.artist = Artist.objects.create(
			name="Test Artist",
			slug="test-artist",
			is_approved=True,
		)
		self.album = Album.objects.create(
			artist=self.artist,
			title="Test Album",
			slug="test-album",
			release_date=date(2020, 1, 2),
			is_approved=True,
		)
		self.song = Song.objects.create(
			album=self.album,
			artist=self.artist,
			title="Test Song",
			slug="test-song",
			track_number=1,
			duration_seconds=123,
			is_approved=True,
		)

		self.username = "alice"
		self.password = "StrongPass123!"
		self.email = "alice@example.com"

	def _register_and_login(self):
		register_res = self.client.post(
			"/api/auth/register/",
			{"username": self.username, "email": self.email, "password": self.password},
			format="json",
		)
		self.assertEqual(register_res.status_code, 201, register_res.data)
		self.assertTrue(register_res.data.get("id"))

		login_res = self.client.post(
			"/api/auth/login/",
			{"username": self.username, "password": self.password},
			format="json",
		)
		self.assertEqual(login_res.status_code, 200, login_res.data)
		access = login_res.data.get("access")
		refresh = login_res.data.get("refresh")
		self.assertTrue(access)
		self.assertTrue(refresh)

		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
		return access, refresh

	def test_full_smoke_flows(self):
		# Accounts: register/login/me
		access, refresh = self._register_and_login()

		me_res = self.client.get("/api/auth/me/")
		self.assertEqual(me_res.status_code, 200)
		self.assertEqual(me_res.data.get("username"), self.username)
		self.assertEqual(me_res.data.get("email"), self.email)

		# Navigation: albums list (paginated)
		albums_res = self.client.get("/api/albums/?page=1")
		self.assertEqual(albums_res.status_code, 200)
		self.assertIn("results", albums_res.data)
		self.assertIn("count", albums_res.data)
		self.assertGreaterEqual(albums_res.data.get("count", 0), 1)
		self.assertTrue(any(a.get("slug") == self.album.slug for a in albums_res.data.get("results", [])))

		# Album/Artist/Song pages
		album_detail = self.client.get(f"/api/albums/{self.album.slug}/")
		self.assertEqual(album_detail.status_code, 200)
		self.assertEqual(album_detail.data.get("slug"), self.album.slug)
		self.assertTrue(any(s.get("slug") == self.song.slug for s in album_detail.data.get("songs", [])))

		artist_detail = self.client.get(f"/api/artists/{self.artist.slug}/")
		self.assertEqual(artist_detail.status_code, 200)
		self.assertEqual(artist_detail.data.get("slug"), self.artist.slug)

		song_detail = self.client.get(f"/api/songs/{self.song.slug}/")
		self.assertEqual(song_detail.status_code, 200)
		self.assertEqual(song_detail.data.get("slug"), self.song.slug)

		# Discovery: search
		search_res = self.client.get("/api/search/?q=Test")
		self.assertEqual(search_res.status_code, 200)
		self.assertTrue(any(a.get("slug") == self.artist.slug for a in search_res.data.get("artists", [])))
		self.assertTrue(any(a.get("slug") == self.album.slug for a in search_res.data.get("albums", [])))
		self.assertTrue(any(s.get("slug") == self.song.slug for s in search_res.data.get("songs", [])))

		# Interactions: rating album
		rate_album = self.client.post(
			f"/api/albums/{self.album.id}/rate/",
			{"rating": 5},
			format="json",
		)
		self.assertIn(rate_album.status_code, (200, 201))
		self.assertEqual(AlbumRating.objects.filter(album=self.album).count(), 1)

		# Import: ratings CSV (update existing rating)
		csv_content = "created_at,rating,album_id,album_title,album_slug,artist_name,artist_slug\n" + (
			f"{date(2026,1,1).isoformat()},4,{self.album.id},{self.album.title},{self.album.slug},{self.artist.name},{self.artist.slug}\n"
		)
		upload = SimpleUploadedFile(
			"ratings.csv",
			csv_content.encode("utf-8"),
			content_type="text/csv",
		)
		import_res = self.client.post(
			"/api/profile/import/?resource=ratings&format=csv",
			{"file": upload},
			format="multipart",
		)
		self.assertEqual(import_res.status_code, 200, getattr(import_res, 'data', None))
		self.assertEqual(AlbumRating.objects.get(user__username=self.username, album=self.album).rating, 4)

		get_album_rating = self.client.get(f"/api/albums/{self.album.id}/rate/")
		self.assertEqual(get_album_rating.status_code, 200)
		self.assertEqual(get_album_rating.data.get("rating"), 4)

		# Interactions: rating song
		rate_song = self.client.post(
			f"/api/songs/{self.song.id}/rate/",
			{"rating": 4},
			format="json",
		)
		self.assertIn(rate_song.status_code, (200, 201))
		self.assertEqual(SongRating.objects.filter(song=self.song).count(), 1)

		get_song_rating = self.client.get(f"/api/songs/{self.song.id}/rate/")
		self.assertEqual(get_song_rating.status_code, 200)
		self.assertEqual(get_song_rating.data.get("rating"), 4)

		# Comments on song (public list + authenticated create)
		public_list_song_comments = self.client.get(f"/api/songs/{self.song.id}/comments/")
		self.assertEqual(public_list_song_comments.status_code, 200)

		unauth_client = APIClient()
		unauth_post_song_comment = unauth_client.post(
			f"/api/songs/{self.song.id}/comments/",
			{"content": "Nice track!"},
			format="json",
		)
		self.assertIn(unauth_post_song_comment.status_code, (401, 403))

		create_song_comment = self.client.post(
			f"/api/songs/{self.song.id}/comments/",
			{"content": "Nice track!"},
			format="json",
		)
		self.assertEqual(create_song_comment.status_code, 201, create_song_comment.data)
		song_comment_id = create_song_comment.data.get("id")
		self.assertTrue(song_comment_id)
		self.assertEqual(SongComment.objects.filter(song=self.song).count(), 1)

		# Reply thread on song comments
		create_song_reply = self.client.post(
			f"/api/songs/{self.song.id}/comments/",
			{"content": "@alice reply", "parent_id": song_comment_id},
			format="json",
		)
		self.assertEqual(create_song_reply.status_code, 201, create_song_reply.data)
		self.assertEqual(create_song_reply.data.get("parent_id"), song_comment_id)
		self.assertEqual(SongComment.objects.filter(song=self.song).count(), 2)

		other_song = Song.objects.create(
			artist=self.artist,
			album=self.album,
			title="Other song",
			slug="other-song",
			track_number=2,
			duration_seconds=111,
			is_approved=True,
		)
		bad_song_reply = self.client.post(
			f"/api/songs/{other_song.id}/comments/",
			{"content": "Wrong parent", "parent_id": song_comment_id},
			format="json",
		)
		self.assertEqual(bad_song_reply.status_code, 400, bad_song_reply.data)

		list_song_comments = self.client.get(f"/api/songs/{self.song.id}/comments/")
		self.assertEqual(list_song_comments.status_code, 200)
		self.assertTrue(any(c.get("id") == song_comment_id for c in list_song_comments.data))

		# Interactions: create review
		create_review = self.client.post(
			f"/api/albums/{self.album.id}/reviews/",
			{"title": "Nice", "content": "Great album."},
			format="json",
		)
		self.assertEqual(create_review.status_code, 201, create_review.data)
		review_id = create_review.data.get("id")
		self.assertTrue(review_id)
		self.assertEqual(AlbumReview.objects.filter(album=self.album).count(), 1)

		# Review list includes likes_count
		reviews_list = self.client.get(f"/api/albums/{self.album.id}/reviews/")
		self.assertEqual(reviews_list.status_code, 200)
		self.assertTrue(any(r.get("id") == review_id for r in reviews_list.data))
		first_review = next(r for r in reviews_list.data if r.get("id") == review_id)
		self.assertIn("likes_count", first_review)

		# Like/unlike review
		like_res = self.client.post(f"/api/reviews/{review_id}/like/", {}, format="json")
		self.assertEqual(like_res.status_code, 200)
		self.assertEqual(like_res.data.get("liked"), True)
		self.assertEqual(AlbumReviewLike.objects.filter(review_id=review_id).count(), 1)

		unlike_res = self.client.delete(f"/api/reviews/{review_id}/like/")
		self.assertEqual(unlike_res.status_code, 200)
		self.assertEqual(unlike_res.data.get("liked"), False)
		self.assertEqual(AlbumReviewLike.objects.filter(review_id=review_id).count(), 0)

		# Edit review
		update_res = self.client.put(
			f"/api/reviews/{review_id}/",
			{"title": "Updated", "content": "Even better."},
			format="json",
		)
		self.assertEqual(update_res.status_code, 200, update_res.data)
		self.assertEqual(update_res.data.get("title"), "Updated")

		# Comments on review (create/list/update/delete + ownership)
		create_comment = self.client.post(
			f"/api/reviews/{review_id}/comments/",
			{"content": "Super review!"},
			format="json",
		)
		self.assertEqual(create_comment.status_code, 201, create_comment.data)
		comment_id = create_comment.data.get("id")
		self.assertTrue(comment_id)
		self.assertEqual(ReviewComment.objects.filter(review_id=review_id).count(), 1)

		# Reply thread: create a reply to the first comment
		create_reply = self.client.post(
			f"/api/reviews/{review_id}/comments/",
			{"content": "Reply", "parent_id": comment_id},
			format="json",
		)
		self.assertEqual(create_reply.status_code, 201, create_reply.data)
		reply_id = create_reply.data.get("id")
		self.assertTrue(reply_id)
		self.assertEqual(create_reply.data.get("parent_id"), comment_id)
		self.assertEqual(ReviewComment.objects.filter(review_id=review_id).count(), 2)

		# parent_id must belong to the same review
		create_review2 = self.client.post(
			f"/api/albums/{self.album.id}/reviews/",
			{"title": "Another", "content": "Second review."},
			format="json",
		)
		self.assertEqual(create_review2.status_code, 201, create_review2.data)
		review2_id = create_review2.data.get("id")
		self.assertTrue(review2_id)
		bad_reply = self.client.post(
			f"/api/reviews/{review2_id}/comments/",
			{"content": "Bad reply", "parent_id": comment_id},
			format="json",
		)
		self.assertEqual(bad_reply.status_code, 400, bad_reply.data)

		list_comments = self.client.get(f"/api/reviews/{review_id}/comments/")
		self.assertEqual(list_comments.status_code, 200)
		self.assertTrue(any(c.get("id") == comment_id for c in list_comments.data))

		# Register/login a different user and ensure they cannot edit/delete
		bob_username = "bob"
		bob_password = "StrongPass123!"
		bob_email = "bob@example.com"
		bob_register = self.client.post(
			"/api/auth/register/",
			{"username": bob_username, "email": bob_email, "password": bob_password},
			format="json",
		)
		self.assertEqual(bob_register.status_code, 201, bob_register.data)
		bob_login = self.client.post(
			"/api/auth/login/",
			{"username": bob_username, "password": bob_password},
			format="json",
		)
		self.assertEqual(bob_login.status_code, 200, bob_login.data)
		bob_access = bob_login.data.get("access")
		self.assertTrue(bob_access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {bob_access}")

		bob_update_comment = self.client.put(
			f"/api/review-comments/{comment_id}/",
			{"content": "Hack"},
			format="json",
		)
		self.assertEqual(bob_update_comment.status_code, 403)
		bob_delete_comment = self.client.delete(f"/api/review-comments/{comment_id}/")
		self.assertEqual(bob_delete_comment.status_code, 403)

		bob_delete_review = self.client.delete(f"/api/reviews/{review_id}/")
		self.assertEqual(bob_delete_review.status_code, 403)

		# Switch back to alice
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

		update_comment = self.client.put(
			f"/api/review-comments/{comment_id}/",
			{"content": "Mersi!"},
			format="json",
		)
		self.assertEqual(update_comment.status_code, 200, update_comment.data)
		self.assertEqual(update_comment.data.get("content"), "Mersi!")

		delete_comment = self.client.delete(f"/api/review-comments/{comment_id}/")
		self.assertEqual(delete_comment.status_code, 204)
		self.assertEqual(ReviewComment.objects.filter(id=comment_id).count(), 0)

		# Social: lists
		create_list = self.client.post("/api/lists", {"name": "Favorites"}, format="json")
		self.assertEqual(create_list.status_code, 201, create_list.data)
		list_id = create_list.data.get("id")
		self.assertTrue(list_id)

		add_album = self.client.post(
			f"/api/lists/{list_id}/albums",
			{"album_id": self.album.id},
			format="json",
		)
		self.assertIn(add_album.status_code, (200, 201), add_album.data)
		self.assertEqual(List.objects.filter(id=list_id).count(), 1)
		self.assertEqual(ListAlbum.objects.filter(list_id=list_id, album=self.album).count(), 1)

		# Social: follow artist
		follow_status = self.client.get(f"/api/artists/{self.artist.id}/follow/")
		self.assertEqual(follow_status.status_code, 200)
		self.assertEqual(follow_status.data.get("is_following"), False)

		follow_res = self.client.post(f"/api/artists/{self.artist.id}/follow/", {}, format="json")
		self.assertIn(follow_res.status_code, (200, 201))
		self.assertEqual(follow_res.data.get("is_following"), True)
		self.assertEqual(ArtistFollow.objects.filter(artist=self.artist).count(), 1)

		following_list = self.client.get("/api/following/artists")
		self.assertEqual(following_list.status_code, 200)
		self.assertTrue(any(a.get("artist_id") == self.artist.id for a in following_list.data))

		unfollow_res = self.client.delete(f"/api/artists/{self.artist.id}/follow/")
		self.assertEqual(unfollow_res.status_code, 200)
		self.assertEqual(unfollow_res.data.get("is_following"), False)
		self.assertEqual(ArtistFollow.objects.filter(artist=self.artist).count(), 0)

		# Discovery: top albums endpoint returns list
		top_res = self.client.get("/api/top-albums/")
		self.assertEqual(top_res.status_code, 200)
		self.assertTrue(isinstance(top_res.data, list))
		self.assertTrue(any(a.get("slug") == self.album.slug for a in top_res.data))

		# Profile: my content endpoints
		my_reviews = self.client.get("/api/profile/reviews")
		self.assertEqual(my_reviews.status_code, 200)
		self.assertTrue(any(r.get("album_slug") == self.album.slug for r in my_reviews.data))

		# Delete review (author only)
		delete_review = self.client.delete(f"/api/reviews/{review_id}/")
		self.assertEqual(delete_review.status_code, 204)
		self.assertEqual(AlbumReview.objects.filter(id=review_id).count(), 0)

		my_ratings = self.client.get("/api/profile/ratings")
		self.assertEqual(my_ratings.status_code, 200)
		self.assertTrue(any(r.get("album_slug") == self.album.slug for r in my_ratings.data.get("albums", {}).get("results", [])))
		self.assertTrue(any(r.get("song_slug") == self.song.slug for r in my_ratings.data.get("songs", {}).get("results", [])))

	def test_profile_ratings_paginates_albums_and_songs(self):
		self._register_and_login()
		from django.contrib.auth import get_user_model

		user = get_user_model().objects.get(username=self.username)

		artist = Artist.objects.create(name="Artist 2", slug="artist-2", is_approved=True)
		for index in range(1, 12):
			album = Album.objects.create(
				artist=artist,
				title=f"Rated Album {index}",
				slug=f"rated-album-{index}",
				release_date=date(2020, 2, min(index, 28)),
				is_approved=True,
			)
			song = Song.objects.create(
				album=album,
				artist=artist,
				title=f"Rated Song {index}",
				slug=f"rated-song-{index}",
				track_number=1,
				duration_seconds=120,
				is_approved=True,
			)
			AlbumRating.objects.create(user=user, album=album, rating=5)
			SongRating.objects.create(user=user, song=song, rating=4)

		page1 = self.client.get("/api/profile/ratings")
		self.assertEqual(page1.status_code, 200, page1.data)
		self.assertEqual(page1.data.get("albums", {}).get("count"), 11)
		self.assertEqual(page1.data.get("songs", {}).get("count"), 11)
		self.assertEqual(len(page1.data.get("albums", {}).get("results", [])), 10)
		self.assertEqual(len(page1.data.get("songs", {}).get("results", [])), 10)

		page2 = self.client.get("/api/profile/ratings/?album_page=2&song_page=2")
		self.assertEqual(page2.status_code, 200, page2.data)
		self.assertEqual(page2.data.get("albums", {}).get("count"), 11)
		self.assertEqual(page2.data.get("songs", {}).get("count"), 11)
		self.assertEqual(len(page2.data.get("albums", {}).get("results", [])), 1)
		self.assertEqual(len(page2.data.get("songs", {}).get("results", [])), 1)
		self.assertEqual(page2.data.get("albums", {}).get("results", [])[0].get("album_slug"), "rated-album-1")
		self.assertEqual(page2.data.get("songs", {}).get("results", [])[0].get("song_slug"), "rated-song-1")

		# Logout (client-side): simulate by removing credentials and checking auth-required endpoints fail
		self.client.credentials()
		lists_unauth = self.client.get("/api/lists")
		self.assertIn(lists_unauth.status_code, (401, 403))


class TestBackgroundRecommendationTasks(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="task-user", password="pw")
		self.artist = Artist.objects.create(name="Task Artist", slug="task-artist", is_approved=True)
		self.album = Album.objects.create(
			artist=self.artist,
			title="Task Album",
			slug="task-album",
			release_date=date(2024, 1, 1),
			is_approved=True,
		)
		AlbumRating.objects.create(user=self.user, album=self.album, rating=5)

	def tearDown(self):
		from django.core.cache import cache
		cache.clear()

	def test_precompute_recommendations_task_calls_recommender_helpers(self):
		with patch("interactions.tasks.compute_and_cache_neighbors") as mock_neighbors, patch(
			"interactions.tasks.compute_and_cache_user_recommendations"
		) as mock_recommendations:
			result = precompute_recommendations.run(limit=7, max_users=1)

		mock_neighbors.assert_called_once_with(k=50)
		mock_recommendations.assert_called_once_with(self.user.id, limit=7)
		self.assertEqual(result.get("status"), "success")
		self.assertEqual(result.get("users_processed"), 1)
		self.assertEqual(result.get("limit"), 7)


class TestBackgroundCompatibilityTasks(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="compat-user", password="pw")
		self.artist = Artist.objects.create(name="Compat Artist", slug="compat-artist", is_approved=True)
		self.album = Album.objects.create(
			artist=self.artist,
			title="Compat Album",
			slug="compat-album",
			release_date=date(2024, 1, 1),
			is_approved=True,
		)
		AlbumRating.objects.create(user=self.user, album=self.album, rating=5)

	def tearDown(self):
		from django.core.cache import cache
		cache.clear()

	def test_precompute_compatibility_calls_similarity_helper(self):
		with patch("interactions.tasks.compute_and_cache_similar_users") as mock_sim:
			result = precompute_compatibility.run(limit=20, max_users=1)

		mock_sim.assert_called_once_with(self.user.id, limit=20)
		self.assertEqual(result.get("status"), "success")
		self.assertEqual(result.get("users_processed"), 1)


class TestGamificationEndpoints(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.username = "bob"
		self.password = "StrongPass123!"
		self.email = "bob@example.com"

		# Seed: Romanian album + 90s album + genres
		self.genre1 = Genre.objects.create(name="Rock", slug="rock")
		self.genre2 = Genre.objects.create(name="Pop", slug="pop")
		self.genre3 = Genre.objects.create(name="Jazz", slug="jazz")

		self.rom_artist = Artist.objects.create(
			name="Romanian Artist",
			slug="romanian-artist",
			is_romanian=True,
			is_approved=True,
		)
		self.int_artist = Artist.objects.create(
			name="International Artist",
			slug="international-artist",
			is_romanian=False,
			is_approved=True,
		)

		self.rom_album = Album.objects.create(
			artist=self.rom_artist,
			title="Ro Album",
			slug="ro-album",
			release_date=date(2001, 1, 1),
			is_approved=True,
		)
		self.rom_album.genres.add(self.genre1)

		self.album_90s = Album.objects.create(
			artist=self.int_artist,
			title="90s Album",
			slug="90s-album",
			release_date=date(1995, 6, 1),
			is_approved=True,
		)
		self.album_90s.genres.add(self.genre2)

		self.album_other = Album.objects.create(
			artist=self.int_artist,
			title="Other Album",
			slug="other-album",
			release_date=date(2010, 1, 1),
			is_approved=True,
		)
		self.album_other.genres.add(self.genre3)

	def _register_and_login(self):
		from django.contrib.auth import get_user_model
		User = get_user_model()

		register_res = self.client.post(
			"/api/auth/register/",
			{"username": self.username, "email": self.email, "password": self.password},
			format="json",
		)
		self.assertEqual(register_res.status_code, 201, register_res.data)
		self.user = User.objects.get(username=self.username)

		login_res = self.client.post(
			"/api/auth/login/",
			{"username": self.username, "password": self.password},
			format="json",
		)
		self.assertEqual(login_res.status_code, 200, login_res.data)
		access = login_res.data.get("access")
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
		return access

	def test_weekly_challenges_and_streak(self):
		self._register_and_login()

		today = timezone.localdate()
		# Create a 3-day listen streak (today, yesterday, 2 days ago)
		for delta in (0, 1, 2):
			AlbumListen.objects.create(
				user=self.user,
				album=self.rom_album,
				listened_date=today - timedelta(days=delta),
			)

		streak_res = self.client.get("/api/profile/streak/")
		self.assertEqual(streak_res.status_code, 200, getattr(streak_res, 'data', None))
		self.assertGreaterEqual(int(streak_res.data.get("listen_streak_days") or 0), 1)
		self.assertIn("rating_streak_days", streak_res.data)
		self.assertIn("activity_streak_days", streak_res.data)

		# Create listens that should satisfy weekly challenges:
		# - Romanian albums (1 distinct)
		# - 90s album (1 distinct)
		# - 3 distinct genres
		AlbumListen.objects.create(user=self.user, album=self.album_90s, listened_date=today)
		AlbumListen.objects.create(user=self.user, album=self.album_other, listened_date=today)

		weekly_res = self.client.get("/api/profile/challenges/weekly/")
		self.assertEqual(weekly_res.status_code, 200, getattr(weekly_res, 'data', None))
		challenges = weekly_res.data.get("challenges")
		self.assertTrue(isinstance(challenges, list))
		self.assertEqual(len(challenges), 3)
		for challenge in challenges:
			self.assertIn("key", challenge)
			self.assertIn("title", challenge)
			self.assertIn("progress", challenge)
			self.assertIn("target", challenge)
			self.assertIn("completed", challenge)

		previous_week_recap = weekly_res.data.get("previous_week_recap")
		self.assertTrue(isinstance(previous_week_recap, dict))
		self.assertTrue(isinstance(previous_week_recap.get("challenges"), list))
		self.assertTrue(isinstance(previous_week_recap.get("completed_challenges"), list))
		self.assertTrue(isinstance(previous_week_recap.get("incomplete_challenges"), list))

		current_payload = weekly_challenges_payload_for(self.user, today=today)
		previous_payload = weekly_challenges_payload_for(self.user, today=today - timedelta(days=7))
		current_keys = [c.get("key") for c in current_payload.get("challenges", [])]
		previous_keys = [c.get("key") for c in previous_payload.get("challenges", [])]
		self.assertEqual(len(current_keys), 3)
		self.assertEqual(len(previous_keys), 3)
		self.assertNotEqual(current_keys, previous_keys)


class TestChatMessagesEndpoint(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.username = "bob"
		self.password = "StrongPass123!"
		self.email = "bob@example.com"

	def _register_and_login(self):
		register_res = self.client.post(
			"/api/auth/register/",
			{"username": self.username, "email": self.email, "password": self.password},
			format="json",
		)
		self.assertEqual(register_res.status_code, 201, register_res.data)

		login_res = self.client.post(
			"/api/auth/login/",
			{"username": self.username, "password": self.password},
			format="json",
		)
		self.assertEqual(login_res.status_code, 200, login_res.data)
		access = login_res.data.get("access")
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_requires_auth(self):
		unauth = APIClient()
		res = unauth.get("/api/chat/messages/")
		self.assertIn(res.status_code, (401, 403))

	def test_post_and_get(self):
		self._register_and_login()

		post_res = self.client.post(
			"/api/chat/messages/",
			{"content": "Salut!"},
			format="json",
		)
		self.assertEqual(post_res.status_code, 201, post_res.data)
		self.assertTrue(post_res.data.get("id"))
		self.assertEqual(post_res.data.get("content"), "Salut!")
		self.assertEqual(ChatMessage.objects.count(), 1)

		get_res = self.client.get("/api/chat/messages/?limit=10")
		self.assertEqual(get_res.status_code, 200)
		self.assertTrue(isinstance(get_res.data, list))
		self.assertTrue(any(m.get("content") == "Salut!" for m in get_res.data))


class TestCorrectionsEndpoint(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.username = "carol"
		self.password = "StrongPass123!"
		self.email = "carol@example.com"

	def _register_and_login(self):
		register_res = self.client.post(
			"/api/auth/register/",
			{"username": self.username, "email": self.email, "password": self.password},
			format="json",
		)
		self.assertEqual(register_res.status_code, 201, register_res.data)

		login_res = self.client.post(
			"/api/auth/login/",
			{"username": self.username, "password": self.password},
			format="json",
		)
		self.assertEqual(login_res.status_code, 200, login_res.data)
		access = login_res.data.get("access")
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_anonymous_can_submit(self):
		unauth = APIClient()
		res = unauth.post(
			"/api/corrections/",
			{"page_url": "https://example.com/page", "description": "E greșit."},
			format="json",
		)
		self.assertEqual(res.status_code, 201, res.data)
		self.assertEqual(CorrectionReport.objects.count(), 1)
		report = CorrectionReport.objects.first()
		self.assertIsNone(report.user)
		self.assertEqual(report.page_url, "https://example.com/page")

	def test_authenticated_report_is_linked(self):
		self._register_and_login()
		res = self.client.post(
			"/api/corrections/",
			{"page_url": "", "description": "Altă corecție."},
			format="json",
		)
		self.assertEqual(res.status_code, 201, res.data)
		report = CorrectionReport.objects.order_by('-id').first()
		self.assertIsNotNone(report.user)


class TestProfileStats(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"

		self.user = self._create_user("alice")
		self.other = self._create_user("bob")

		self.genre_rock = Genre.objects.create(name="Rock", slug="rock")
		self.genre_jazz = Genre.objects.create(name="Jazz", slug="jazz")

		artist_a = Artist.objects.create(name="Artist A", slug="artist-a", is_approved=True)
		artist_b = Artist.objects.create(name="Artist B", slug="artist-b", is_approved=True)

		self.album1 = Album.objects.create(artist=artist_a, title="A1", slug="a1", release_date=date(2020, 1, 1), is_approved=True)
		self.album1.genres.add(self.genre_rock)

		self.album2 = Album.objects.create(artist=artist_a, title="A2", slug="a2", release_date=date(2020, 1, 2), is_approved=True)
		self.album2.genres.add(self.genre_rock)

		self.album3 = Album.objects.create(artist=artist_b, title="B1", slug="b1", release_date=date(2020, 1, 3), is_approved=True)
		self.album3.genres.add(self.genre_jazz)

	def _create_user(self, username: str):
		from django.contrib.auth import get_user_model
		User = get_user_model()
		return User.objects.create_user(username=username, password=self.password)

	def _login(self, username: str):
		res = self.client.post("/api/auth/login/", {"username": username, "password": self.password}, format="json")
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get("access")
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_profile_stats_empty(self):
		self._login("alice")
		res = self.client.get("/api/profile/stats")
		self.assertEqual(res.status_code, 200)
		self.assertIn("favorite_albums", res.data)
		self.assertIn("favorite_songs", res.data)
		self.assertTrue(isinstance(res.data.get("favorite_albums"), list))
		self.assertTrue(isinstance(res.data.get("favorite_songs"), list))
		self.assertEqual(len(res.data.get("favorite_albums")), 4)
		self.assertEqual(len(res.data.get("favorite_songs")), 4)
		self.assertEqual(
			[slot.get("album_id") for slot in res.data.get("favorite_albums")],
			[None, None, None, None],
		)
		self.assertEqual(
			[slot.get("song_id") for slot in res.data.get("favorite_songs")],
			[None, None, None, None],
		)
		self.assertEqual(res.data.get("total_ratings"), 0)
		self.assertIsNone(res.data.get("average_rating_given"))
		self.assertIsNone(res.data.get("favorite_genre"))
		self.assertIsNone(res.data.get("favorite_artist"))
		self.assertEqual(
			res.data.get("ratings_distribution"),
			[
				{"stars": 5, "count": 0},
				{"stars": 4, "count": 0},
				{"stars": 3, "count": 0},
				{"stars": 2, "count": 0},
				{"stars": 1, "count": 0},
			],
		)
		self.assertEqual(res.data.get("top_genres_rated"), [])
		self.assertEqual(
			res.data.get("activity"),
			{
				"reviews_written": 0,
				"albums_rated": 0,
				"artists_followed": 0,
				"lists_created": 0,
			},
		)

	def test_profile_stats_computed(self):
		AlbumRating.objects.create(user=self.user, album=self.album1, rating=5)
		AlbumRating.objects.create(user=self.user, album=self.album2, rating=4)
		AlbumRating.objects.create(user=self.user, album=self.album3, rating=3)
		AlbumReview.objects.create(user=self.user, album=self.album1, title="t", content="c")
		ArtistFollow.objects.create(user=self.user, artist=self.album1.artist)
		List.objects.create(user=self.user, name="L1")

		# Other user's ratings shouldn't affect alice stats
		AlbumRating.objects.create(user=self.other, album=self.album1, rating=1)

		self._login("alice")
		res = self.client.get("/api/profile/stats")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertEqual(res.data.get("total_ratings"), 3)
		self.assertEqual(res.data.get("average_rating_given"), 4.0)
		# Rock appears in album1 and album2 => most rated genre
		self.assertEqual(res.data.get("favorite_genre"), "Rock")
		# Artist A has 2 ratings (album1+album2)
		self.assertEqual(res.data.get("favorite_artist"), "Artist A")

		dist = res.data.get("ratings_distribution")
		self.assertEqual(
			dist,
			[
				{"stars": 5, "count": 1},
				{"stars": 4, "count": 1},
				{"stars": 3, "count": 1},
				{"stars": 2, "count": 0},
				{"stars": 1, "count": 0},
			],
		)

		top_genres = res.data.get("top_genres_rated")
		self.assertEqual(top_genres[0].get("name"), "Rock")
		self.assertEqual(top_genres[0].get("ratings"), 2)
		self.assertEqual(top_genres[1].get("name"), "Jazz")
		self.assertEqual(top_genres[1].get("ratings"), 1)

		self.assertEqual(
			res.data.get("activity"),
			{
				"reviews_written": 1,
				"albums_rated": 3,
				"artists_followed": 1,
				"lists_created": 1,
			},
		)

	def test_profile_favorite_songs_set_and_get(self):
		self._login("alice")

		song1 = Song.objects.create(artist=self.album1.artist, album=self.album1, title="Song 1", slug="song-1", track_number=1, is_approved=True)
		song2 = Song.objects.create(artist=self.album1.artist, album=self.album2, title="Song 2", slug="song-2", track_number=1, is_approved=True)
		song3 = Song.objects.create(artist=self.album1.artist, album=None, title="Song 3", slug="song-3", is_approved=True)
		album = Album.objects.create(
			artist=self.album1.artist,
			title="Single Album",
			slug="single-album",
			release_date=date(2020, 1, 5),
			is_approved=True,
		)
		song4 = Song.objects.create(artist=self.album1.artist, album=album, title="Song 4", slug="song-4", track_number=1, is_approved=True)

		put_res = self.client.put(
			"/api/profile/favorite-songs",
			{"slots": [song1.id, song2.id, None, song4.id]},
			format="json",
		)
		self.assertEqual(put_res.status_code, 200, put_res.data)
		fav = put_res.data.get("favorite_songs")
		self.assertEqual([s.get("song_id") for s in fav], [song1.id, song2.id, None, song4.id])
		self.assertEqual(FavoriteSong.objects.filter(user=self.user).count(), 3)

		get_res = self.client.get("/api/profile/favorite-songs")
		self.assertEqual(get_res.status_code, 200, get_res.data)
		fav2 = get_res.data.get("favorite_songs")
		self.assertEqual([s.get("song_id") for s in fav2], [song1.id, song2.id, None, song4.id])

		stats_res = self.client.get("/api/profile/stats")
		self.assertEqual(stats_res.status_code, 200, stats_res.data)
		fav3 = stats_res.data.get("favorite_songs")
		self.assertEqual([s.get("song_id") for s in fav3], [song1.id, song2.id, None, song4.id])

		dup_res = self.client.put(
			"/api/profile/favorite-songs",
			{"slots": [song1.id, song1.id, None, None]},
			format="json",
		)
		self.assertEqual(dup_res.status_code, 400)

		unapproved = Song.objects.create(
			artist=self.album1.artist,
			album=self.album1,
			title="Nope",
			slug="song-nope",
			track_number=2,
			is_approved=False,
		)
		bad_res = self.client.put(
			"/api/profile/favorite-songs",
			{"slots": [unapproved.id, None, None, None]},
			format="json",
		)
		self.assertEqual(bad_res.status_code, 400)

	def test_profile_favorite_albums_set_and_get(self):
		self._login("alice")

		put_res = self.client.put(
			"/api/profile/favorite-albums",
			{"slots": [self.album1.id, self.album2.id, None, self.album3.id]},
			format="json",
		)
		self.assertEqual(put_res.status_code, 200, put_res.data)
		fav = put_res.data.get("favorite_albums")
		self.assertEqual([s.get("album_id") for s in fav], [self.album1.id, self.album2.id, None, self.album3.id])
		self.assertEqual(FavoriteAlbum.objects.filter(user=self.user).count(), 3)

		get_res = self.client.get("/api/profile/favorite-albums")
		self.assertEqual(get_res.status_code, 200, get_res.data)
		fav2 = get_res.data.get("favorite_albums")
		self.assertEqual([s.get("album_id") for s in fav2], [self.album1.id, self.album2.id, None, self.album3.id])

		stats_res = self.client.get("/api/profile/stats")
		self.assertEqual(stats_res.status_code, 200, stats_res.data)
		fav3 = stats_res.data.get("favorite_albums")
		self.assertEqual([s.get("album_id") for s in fav3], [self.album1.id, self.album2.id, None, self.album3.id])

		# Duplicate album ids are rejected
		dup_res = self.client.put(
			"/api/profile/favorite-albums",
			{"slots": [self.album1.id, self.album1.id, None, None]},
			format="json",
		)
		self.assertEqual(dup_res.status_code, 400)

		# Unapproved album is rejected
		unapproved = Album.objects.create(
			artist=self.album1.artist,
			title="Nope",
			slug="nope",
			release_date=date(2020, 1, 4),
			is_approved=False,
		)
		bad_res = self.client.put(
			"/api/profile/favorite-albums",
			{"slots": [unapproved.id, None, None, None]},
			format="json",
		)
		self.assertEqual(bad_res.status_code, 400)


class TestFriends(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"

		from django.contrib.auth import get_user_model
		User = get_user_model()
		self.alice = User.objects.create_user(username='alice', password=self.password)
		self.bob = User.objects.create_user(username='bob', password=self.password)
		self.carla = User.objects.create_user(username='carla', password=self.password)

	def _login(self, username: str):
		res = self.client.post(
			"/api/auth/login/",
			{"username": username, "password": self.password},
			format="json",
		)
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get('access')
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_send_and_accept_friend_request(self):
		self._login('alice')
		create_res = self.client.post(
			"/api/friends/request",
			{"receiver_username": "bob"},
			format="json",
		)
		self.assertIn(create_res.status_code, (200, 201), create_res.data)
		request_id = create_res.data.get('id')
		self.assertTrue(request_id)
		self.assertEqual(FriendRequest.objects.count(), 1)

		# Bob accepts
		self.client.credentials()
		self._login('bob')
		accept_res = self.client.post(
			"/api/friends/accept",
			{"request_id": request_id},
			format="json",
		)
		self.assertEqual(accept_res.status_code, 200, accept_res.data)
		self.assertEqual(accept_res.data.get('status'), 'accepted')

		# Friends list shows each other
		list_res = self.client.get("/api/friends/list")
		self.assertEqual(list_res.status_code, 200, list_res.data)
		friends = list_res.data.get('friends', {}).get('results', [])
		self.assertTrue(any(u.get('username') == 'alice' for u in friends))

		self.client.credentials()
		self._login('alice')
		list_res2 = self.client.get("/api/friends/list")
		self.assertEqual(list_res2.status_code, 200, list_res2.data)
		friends2 = list_res2.data.get('friends', {}).get('results', [])
		self.assertTrue(any(u.get('username') == 'bob' for u in friends2))

	def test_friends_list_paginates_at_ten_items(self):
		from django.contrib.auth import get_user_model

		User = get_user_model()
		self._login('alice')
		for index in range(1, 12):
			other = User.objects.create_user(username=f"friend{index}", password=self.password)
			FriendRequest.objects.create(
				sender=self.alice,
				receiver=other,
				status=FriendRequest.Status.ACCEPTED,
			)

		page1 = self.client.get("/api/friends/list")
		self.assertEqual(page1.status_code, 200, page1.data)
		self.assertEqual(page1.data.get('friends', {}).get('count'), 11)
		self.assertEqual(len(page1.data.get('friends', {}).get('results', [])), 10)

		page2 = self.client.get("/api/friends/list/?page=2")
		self.assertEqual(page2.status_code, 200, page2.data)
		self.assertEqual(page2.data.get('friends', {}).get('count'), 11)
		self.assertEqual(len(page2.data.get('friends', {}).get('results', [])), 1)

	def test_reject_friend_request(self):
		self._login('carla')
		create_res = self.client.post(
			"/api/friends/request",
			{"receiver_username": "bob"},
			format="json",
		)
		self.assertIn(create_res.status_code, (200, 201), create_res.data)
		request_id = create_res.data.get('id')
		self.assertTrue(request_id)

		self.client.credentials()
		self._login('bob')
		reject_res = self.client.post(
			"/api/friends/reject",
			{"request_id": request_id},
			format="json",
		)
		self.assertEqual(reject_res.status_code, 200, reject_res.data)
		self.assertEqual(reject_res.data.get('status'), 'rejected')

		list_res = self.client.get("/api/friends/list")
		self.assertEqual(list_res.status_code, 200, list_res.data)
		self.assertEqual(list_res.data.get('incoming'), [])

	def test_cannot_send_friend_request_to_self(self):
		self._login('alice')
		res = self.client.post(
			"/api/friends/request",
			{"receiver_username": "alice"},
			format="json",
		)
		self.assertEqual(res.status_code, 400)

	def test_only_receiver_can_accept(self):
		self._login('alice')
		create_res = self.client.post(
			"/api/friends/request",
			{"receiver_username": "bob"},
			format="json",
		)
		request_id = create_res.data.get('id')

		# Sender cannot accept (404 due to receiver filter)
		res = self.client.post(
			"/api/friends/accept",
			{"request_id": request_id},
			format="json",
		)
		self.assertEqual(res.status_code, 404)


class TestProfileListens(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"

		from django.contrib.auth import get_user_model
		User = get_user_model()
		self.user = User.objects.create_user(username='alice', password=self.password)

		artist = Artist.objects.create(name="Artist", slug="artist", is_approved=True)
		self.album1 = Album.objects.create(artist=artist, title="A1", slug="a1", release_date=date(2020, 1, 1), is_approved=True)
		self.album2 = Album.objects.create(artist=artist, title="A2", slug="a2", release_date=date(2020, 1, 2), is_approved=True)

	def _login(self):
		res = self.client.post(
			"/api/auth/login/",
			{"username": "alice", "password": self.password},
			format="json",
		)
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get('access')
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_profile_listens_requires_auth(self):
		res = self.client.get("/api/profile/listens")
		self.assertIn(res.status_code, (401, 403))

	def test_profile_listens_returns_list_and_is_ordered(self):
		from django.utils import timezone
		from datetime import timedelta

		# Create listens and force deterministic listened_at ordering.
		l1 = AlbumListen.objects.create(user=self.user, album=self.album1, listened_date=date(2025, 1, 1))
		l2 = AlbumListen.objects.create(user=self.user, album=self.album2, listened_date=date(2025, 1, 2))

		now = timezone.now()
		AlbumListen.objects.filter(id=l1.id).update(listened_at=now - timedelta(days=2))
		AlbumListen.objects.filter(id=l2.id).update(listened_at=now - timedelta(days=1))

		self._login()
		res = self.client.get("/api/profile/listens")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))
		self.assertEqual(len(res.data), 2)
		# Most recent first
		self.assertEqual(res.data[0].get('album_slug'), 'a2')
		self.assertEqual(res.data[1].get('album_slug'), 'a1')


class TestProfileListensStats(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"

		from django.contrib.auth import get_user_model
		User = get_user_model()
		self.user = User.objects.create_user(username='alice', password=self.password)

		artist = Artist.objects.create(name="Artist", slug="artist", is_approved=True)
		self.album1 = Album.objects.create(artist=artist, title="A1", slug="a1", release_date=date(2020, 1, 1), is_approved=True)
		self.album2 = Album.objects.create(artist=artist, title="A2", slug="a2", release_date=date(2020, 1, 2), is_approved=True)

	def _login(self):
		res = self.client.post(
			"/api/auth/login/",
			{"username": "alice", "password": self.password},
			format="json",
		)
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get('access')
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_profile_listens_stats_requires_auth(self):
		res = self.client.get("/api/profile/listens/stats")
		self.assertIn(res.status_code, (401, 403))

	def test_profile_listens_stats_returns_distinct_counts(self):
		from django.utils import timezone
		year = timezone.localdate().year

		# album1 listened twice this year (distinct album count should remain 1)
		AlbumListen.objects.create(user=self.user, album=self.album1, listened_date=date(year, 1, 1))
		AlbumListen.objects.create(user=self.user, album=self.album1, listened_date=date(year, 2, 1))
		# album2 listened last year
		AlbumListen.objects.create(user=self.user, album=self.album2, listened_date=date(year - 1, 12, 31))

		self._login()
		res = self.client.get("/api/profile/listens/stats")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertEqual(res.data.get('year'), year)
		self.assertEqual(res.data.get('total_albums'), 2)
		self.assertEqual(res.data.get('year_albums'), 1)


class TestWantToListen(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"

		from django.contrib.auth import get_user_model
		User = get_user_model()
		self.user = User.objects.create_user(username='alice', password=self.password)

		artist = Artist.objects.create(name="Artist", slug="artist", is_approved=True)
		self.album = Album.objects.create(
			artist=artist,
			title="A1",
			slug="a1",
			release_date=date(2020, 1, 1),
			is_approved=True,
		)

	def _login(self):
		res = self.client.post(
			"/api/auth/login/",
			{"username": "alice", "password": self.password},
			format="json",
		)
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get('access')
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_want_to_listen_requires_auth(self):
		res = self.client.get(f"/api/albums/{self.album.id}/want-to-listen")
		self.assertIn(res.status_code, (401, 403))

	def test_want_to_listen_toggle_and_profile_list(self):
		self._login()

		# Initially false
		res = self.client.get(f"/api/albums/{self.album.id}/want-to-listen")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertEqual(res.data.get('wanted'), False)

		# Add
		res = self.client.post(f"/api/albums/{self.album.id}/want-to-listen", {}, format='json')
		self.assertIn(res.status_code, (200, 201), res.data)
		self.assertEqual(res.data.get('wanted'), True)
		self.assertEqual(WantToListen.objects.filter(user=self.user, album=self.album).count(), 1)

		# Add again (idempotent)
		res2 = self.client.post(f"/api/albums/{self.album.id}/want-to-listen", {}, format='json')
		self.assertIn(res2.status_code, (200, 201), res2.data)
		self.assertEqual(res2.data.get('wanted'), True)
		self.assertEqual(WantToListen.objects.filter(user=self.user, album=self.album).count(), 1)

		# Profile list
		list_res = self.client.get("/api/profile/want-to-listen")
		self.assertEqual(list_res.status_code, 200, list_res.data)
		self.assertTrue(isinstance(list_res.data, dict))
		self.assertEqual(list_res.data.get('count'), 1)
		self.assertTrue(isinstance(list_res.data.get('results'), list))
		self.assertEqual(len(list_res.data.get('results')), 1)
		self.assertEqual(list_res.data.get('results')[0].get('album_slug'), 'a1')

		# Remove
		del_res = self.client.delete(f"/api/albums/{self.album.id}/want-to-listen")
		self.assertEqual(del_res.status_code, 200, del_res.data)
		self.assertEqual(del_res.data.get('wanted'), False)
		self.assertEqual(WantToListen.objects.filter(user=self.user, album=self.album).count(), 0)

	def test_mark_listened_removes_from_want_to_listen(self):
		self._login()

		# Add to Want To Listen
		add_res = self.client.post(f"/api/albums/{self.album.id}/want-to-listen", {}, format='json')
		self.assertIn(add_res.status_code, (200, 201), add_res.data)
		self.assertEqual(WantToListen.objects.filter(user=self.user, album=self.album).count(), 1)

		# Mark listened -> should auto-remove from Want To Listen
		listen_res = self.client.post(f"/api/albums/{self.album.id}/listen", {}, format='json')
		self.assertIn(listen_res.status_code, (200, 201), listen_res.data)
		self.assertEqual(listen_res.data.get('listened_today'), True)
		self.assertEqual(WantToListen.objects.filter(user=self.user, album=self.album).count(), 0)

		status_res = self.client.get(f"/api/albums/{self.album.id}/want-to-listen")
		self.assertEqual(status_res.status_code, 200, status_res.data)
		self.assertEqual(status_res.data.get('wanted'), False)

	def test_profile_want_to_listen_paginates_at_ten_items(self):
		self._login()

		artist = Artist.objects.create(name="Artist 2", slug="artist-2", is_approved=True)
		for index in range(1, 12):
			album = Album.objects.create(
				artist=artist,
				title=f"Album {index}",
				slug=f"album-{index}",
				release_date=date(2020, 1, min(index, 28)),
				is_approved=True,
			)
			WantToListen.objects.create(user=self.user, album=album)

		page1 = self.client.get("/api/profile/want-to-listen")
		self.assertEqual(page1.status_code, 200, page1.data)
		self.assertEqual(page1.data.get('count'), 11)
		self.assertEqual(len(page1.data.get('results')), 10)

		page2 = self.client.get("/api/profile/want-to-listen/?page=2")
		self.assertEqual(page2.status_code, 200, page2.data)
		self.assertEqual(page2.data.get('count'), 11)
		self.assertEqual(len(page2.data.get('results')), 1)
		self.assertEqual(page2.data.get('results')[0].get('album_slug'), 'album-1')


class TestListsRemoveAlbum(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"

		from django.contrib.auth import get_user_model
		User = get_user_model()
		self.user = User.objects.create_user(username='alice', password=self.password)

		artist = Artist.objects.create(name="Artist", slug="artist", is_approved=True)
		self.album = Album.objects.create(
			artist=artist,
			title="A1",
			slug="a1",
			release_date=date(2020, 1, 1),
			is_approved=True,
		)

	def _login(self):
		res = self.client.post(
			"/api/auth/login/",
			{"username": "alice", "password": self.password},
			format="json",
		)
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get('access')
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_remove_album_from_list_via_delete_albums_endpoint(self):
		self._login()
		create_list = self.client.post("/api/lists", {"name": "Favorites"}, format="json")
		self.assertEqual(create_list.status_code, 201, create_list.data)
		list_id = create_list.data.get('id')
		self.assertTrue(list_id)

		add_album = self.client.post(
			f"/api/lists/{list_id}/albums",
			{"album_id": self.album.id},
			format="json",
		)
		self.assertIn(add_album.status_code, (200, 201), add_album.data)
		self.assertEqual(ListAlbum.objects.filter(list_id=list_id, album=self.album).count(), 1)

		remove_res = self.client.delete(
			f"/api/lists/{list_id}/albums",
			{"album_id": self.album.id},
			format="json",
		)
		self.assertEqual(remove_res.status_code, 200, remove_res.data)
		self.assertEqual(ListAlbum.objects.filter(list_id=list_id, album=self.album).count(), 0)


class TestProfileTopStats(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"

		from django.contrib.auth import get_user_model
		User = get_user_model()
		self.user = User.objects.create_user(username='alice', password=self.password)

		artist = Artist.objects.create(name="Artist", slug="artist", is_approved=True)
		genre = Genre.objects.create(name="Rock", slug="rock")
		self.album = Album.objects.create(artist=artist, title="A1", slug="a1", release_date=date(2020, 1, 1), is_approved=True)
		self.album.genres.add(genre)
		# Duration: 60 + 120 = 180 seconds
		s1 = Song.objects.create(album=self.album, artist=artist, title="S1", slug="s1", duration_seconds=60, is_approved=True)
		s2 = Song.objects.create(album=self.album, artist=artist, title="S2", slug="s2", duration_seconds=120, is_approved=True)
		self.song1 = s1
		self.song2 = s2

	def _login(self):
		res = self.client.post(
			"/api/auth/login/",
			{"username": "alice", "password": self.password},
			format="json",
		)
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get('access')
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_profile_top_month_stats(self):
		# 2 consecutive days then a gap then another day -> best streak = 2, current streak = 1.
		AlbumListen.objects.create(user=self.user, album=self.album, listened_date=date(2025, 3, 1))
		AlbumListen.objects.create(user=self.user, album=self.album, listened_date=date(2025, 3, 2))
		AlbumListen.objects.create(user=self.user, album=self.album, listened_date=date(2025, 3, 4))

		from django.utils import timezone
		from datetime import datetime

		r1 = SongRating.objects.create(user=self.user, song=self.song1, rating=5)
		r2 = SongRating.objects.create(user=self.user, song=self.song2, rating=3)
		# Force ratings inside March 2025.
		SongRating.objects.filter(id=r1.id).update(
			created_at=timezone.make_aware(datetime(2025, 3, 3, 12, 0, 0)),
		)
		SongRating.objects.filter(id=r2.id).update(
			created_at=timezone.make_aware(datetime(2025, 3, 2, 12, 0, 0)),
		)

		self._login()
		res = self.client.get("/api/profile/top?period=month&year=2025&month=3")
		self.assertEqual(res.status_code, 200, res.data)

		self.assertEqual(res.data.get('period', {}).get('type'), 'month')
		totals = res.data.get('totals') or {}
		self.assertEqual(totals.get('listen_events'), 3)
		self.assertEqual(totals.get('listen_days'), 3)
		self.assertEqual(totals.get('distinct_albums'), 1)
		# Total seconds = 3 listens * 180 sec
		self.assertEqual(totals.get('total_listen_seconds'), 540)

		streak = res.data.get('streak') or {}
		self.assertEqual(streak.get('best_days'), 2)
		self.assertEqual(streak.get('current_days'), 1)

		top_albums = res.data.get('top_albums') or []
		self.assertTrue(top_albums)
		self.assertEqual(top_albums[0].get('album_slug'), 'a1')
		self.assertEqual(top_albums[0].get('listens'), 3)

		top_artists = res.data.get('top_artists') or []
		self.assertTrue(top_artists)
		self.assertEqual(top_artists[0].get('artist_slug'), 'artist')
		self.assertEqual(top_artists[0].get('listens'), 3)

		top_genres = res.data.get('top_genres') or []
		self.assertTrue(top_genres)
		self.assertEqual(top_genres[0].get('genre_slug'), 'rock')
		self.assertEqual(top_genres[0].get('listens'), 3)

		top_songs = res.data.get('top_songs') or []
		self.assertEqual(res.data.get('top_songs_source'), 'song_ratings')
		self.assertEqual(len(top_songs), 2)
		# Highest rating first.
		self.assertEqual(top_songs[0].get('song_slug'), 's1')
		self.assertEqual(top_songs[0].get('rating'), 5)

		comparison = res.data.get('comparison') or {}
		self.assertTrue(comparison.get('available'))
		comparison_totals = comparison.get('totals') or {}
		self.assertEqual(comparison_totals.get('listen_events', {}).get('delta'), 3)


class TestProfileLikedAlbums(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"

		from django.contrib.auth import get_user_model
		User = get_user_model()
		self.user = User.objects.create_user(username='alice', password=self.password)

		artist = Artist.objects.create(name="Artist", slug="artist", is_approved=True)
		self.album1 = Album.objects.create(
			artist=artist,
			title="A1",
			slug="a1",
			release_date=date(2020, 1, 1),
			is_approved=True,
		)
		self.album2 = Album.objects.create(
			artist=artist,
			title="A2",
			slug="a2",
			release_date=date(2020, 1, 2),
			is_approved=True,
		)

	def _login(self):
		res = self.client.post(
			"/api/auth/login/",
			{"username": "alice", "password": self.password},
			format="json",
		)
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get('access')
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_profile_liked_albums_requires_auth(self):
		res = self.client.get("/api/profile/liked-albums")
		self.assertIn(res.status_code, (401, 403))

	def test_profile_liked_albums_returns_explicit_likes(self):
		AlbumLike.objects.create(user=self.user, album=self.album1)

		self._login()

		res = self.client.get("/api/profile/liked-albums")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, dict))
		self.assertEqual(res.data.get('count'), 1)
		self.assertEqual(len(res.data.get('results', [])), 1)
		self.assertEqual(res.data.get('results')[0].get('album_slug'), 'a1')

	def test_profile_liked_albums_paginates_at_ten_items(self):
		self._login()

		artist = Artist.objects.create(name="Artist 2", slug="artist-2", is_approved=True)
		for index in range(1, 12):
			album = Album.objects.create(
				artist=artist,
				title=f"Liked Album {index}",
				slug=f"liked-album-{index}",
				release_date=date(2020, 2, min(index, 28)),
				is_approved=True,
			)
			AlbumLike.objects.create(user=self.user, album=album)

		page1 = self.client.get("/api/profile/liked-albums")
		self.assertEqual(page1.status_code, 200, page1.data)
		self.assertEqual(page1.data.get('count'), 11)
		self.assertEqual(len(page1.data.get('results', [])), 10)

		page2 = self.client.get("/api/profile/liked-albums/?page=2")
		self.assertEqual(page2.status_code, 200, page2.data)
		self.assertEqual(page2.data.get('count'), 11)
		self.assertEqual(len(page2.data.get('results', [])), 1)
		self.assertEqual(page2.data.get('results')[0].get('album_slug'), 'liked-album-1')

	def test_album_like_toggle_endpoints(self):
		# Requires auth
		unauth_status = self.client.get(f"/api/albums/{self.album1.id}/like")
		self.assertIn(unauth_status.status_code, (401, 403))

		self._login()

		status1 = self.client.get(f"/api/albums/{self.album1.id}/like")
		self.assertEqual(status1.status_code, 200, status1.data)
		self.assertEqual(status1.data.get('liked'), False)
		self.assertEqual(status1.data.get('likes_count'), 0)

		add1 = self.client.post(f"/api/albums/{self.album1.id}/like", {}, format='json')
		self.assertIn(add1.status_code, (200, 201), add1.data)
		self.assertEqual(add1.data.get('liked'), True)
		self.assertEqual(add1.data.get('likes_count'), 1)
		self.assertEqual(AlbumLike.objects.filter(user=self.user, album=self.album1).count(), 1)

		status2 = self.client.get(f"/api/albums/{self.album1.id}/like")
		self.assertEqual(status2.status_code, 200, status2.data)
		self.assertEqual(status2.data.get('liked'), True)
		self.assertEqual(status2.data.get('likes_count'), 1)

		del1 = self.client.delete(f"/api/albums/{self.album1.id}/like")
		self.assertEqual(del1.status_code, 200, del1.data)
		self.assertEqual(del1.data.get('liked'), False)
		self.assertEqual(del1.data.get('likes_count'), 0)
		self.assertEqual(AlbumLike.objects.filter(user=self.user, album=self.album1).count(), 0)


class TestSongLikeEndpoints(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"

		from django.contrib.auth import get_user_model
		User = get_user_model()
		self.user = User.objects.create_user(username='alice', password=self.password)

		artist = Artist.objects.create(name="Artist", slug="artist", is_approved=True)
		album = Album.objects.create(
			artist=artist,
			title="A1",
			slug="a1",
			release_date=date(2020, 1, 1),
			is_approved=True,
		)
		self.song = Song.objects.create(
			artist=artist,
			album=album,
			title="S1",
			slug="s1",
			track_number=1,
			duration_seconds=123,
			is_approved=True,
		)

	def _login(self):
		res = self.client.post(
			"/api/auth/login/",
			{"username": "alice", "password": self.password},
			format="json",
		)
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get('access')
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_song_like_toggle_endpoints(self):
		unauth_status = self.client.get(f"/api/songs/{self.song.id}/like")
		self.assertIn(unauth_status.status_code, (401, 403))

		self._login()

		status1 = self.client.get(f"/api/songs/{self.song.id}/like")
		self.assertEqual(status1.status_code, 200, status1.data)
		self.assertEqual(status1.data.get('liked'), False)
		self.assertEqual(status1.data.get('likes_count'), 0)

		add1 = self.client.post(f"/api/songs/{self.song.id}/like", {}, format='json')
		self.assertIn(add1.status_code, (200, 201), add1.data)
		self.assertEqual(add1.data.get('liked'), True)
		self.assertEqual(add1.data.get('likes_count'), 1)
		self.assertEqual(SongLike.objects.filter(user=self.user, song=self.song).count(), 1)

		status2 = self.client.get(f"/api/songs/{self.song.id}/like")
		self.assertEqual(status2.status_code, 200, status2.data)
		self.assertEqual(status2.data.get('liked'), True)
		self.assertEqual(status2.data.get('likes_count'), 1)

		del1 = self.client.delete(f"/api/songs/{self.song.id}/like")
		self.assertEqual(del1.status_code, 200, del1.data)
		self.assertEqual(del1.data.get('liked'), False)
		self.assertEqual(del1.data.get('likes_count'), 0)
		self.assertEqual(SongLike.objects.filter(user=self.user, song=self.song).count(), 0)


class TestActivityFeed(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"

		from django.contrib.auth import get_user_model
		User = get_user_model()
		self.alex = User.objects.create_user(username='alex', password=self.password)
		self.maria = User.objects.create_user(username='maria', password=self.password)
		self.viewer = User.objects.create_user(username='viewer', password=self.password)

		from music.models import Artist, Album
		from datetime import date
		self.artist = Artist.objects.create(name='Puya', slug='puya', is_approved=True)
		self.album = Album.objects.create(
			artist=self.artist,
			title='Romanisme',
			slug='romanisme',
			release_date=date(2020, 1, 1),
			is_approved=True,
		)

	def _login(self, username: str):
		res = self.client.post(
			"/api/auth/login/",
			{"username": username, "password": self.password},
			format="json",
		)
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get('access')
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_activity_is_saved_and_feed_returns_other_users(self):
		# Alex rates an album
		self._login('alex')
		listen_res = self.client.post(
			f"/api/albums/{self.album.id}/listen/",
			{},
			format='json',
		)
		self.assertIn(listen_res.status_code, (200, 201), listen_res.data)
		rate_res = self.client.post(
			f"/api/albums/{self.album.id}/rate/",
			{"rating": 5},
			format='json',
		)
		self.assertIn(rate_res.status_code, (200, 201), rate_res.data)

		# Maria reviews the same album
		self.client.credentials()
		self._login('maria')
		review_res = self.client.post(
			f"/api/albums/{self.album.id}/reviews/",
			{"title": "", "content": "Nice"},
			format='json',
		)
		self.assertEqual(review_res.status_code, 201, review_res.data)

		# Maria follows an artist
		follow_res = self.client.post(
			f"/api/artists/{self.artist.id}/follow/",
			{},
			format='json',
		)
		self.assertIn(follow_res.status_code, (200, 201), follow_res.data)

		# Maria creates a list
		list_res = self.client.post(
			"/api/lists",
			{"name": "Favorites"},
			format='json',
		)
		self.assertEqual(list_res.status_code, 201, list_res.data)

		self.assertGreaterEqual(UserActivity.objects.count(), 4)

		# Viewer fetches activity feed and should see Alex+Maria entries (not viewer)
		self.client.credentials()
		self._login('viewer')
		feed_res = self.client.get('/api/activity?limit=20')
		self.assertEqual(feed_res.status_code, 200)
		self.assertTrue(isinstance(feed_res.data, list))
		self.assertTrue(any(a.get('actor_username') == 'alex' for a in feed_res.data))
	def test_following_activity_feed_only_followed_artists(self):
		from datetime import date
		from music.models import Album, Artist

		other_artist = Artist.objects.create(name='Other', slug='other', is_approved=True)
		other_album = Album.objects.create(
			artist=other_artist,
			title='Other Album',
			slug='other-album',
			release_date=date(2020, 1, 1),
			is_approved=True,
		)

		# Alex creates activity on followed artist album
		self._login('alex')
		res1 = self.client.post(f"/api/albums/{self.album.id}/rate/", {"rating": 4}, format='json')
		self.assertIn(res1.status_code, (200, 201), res1.data)

		# Maria creates activity on non-followed artist album
		self.client.credentials()
		self._login('maria')
		res2 = self.client.post(f"/api/albums/{other_album.id}/rate/", {"rating": 5}, format='json')
		self.assertIn(res2.status_code, (200, 201), res2.data)

		# Viewer follows only Puya
		self.client.credentials()
		self._login('viewer')
		follow = self.client.post(f"/api/artists/{self.artist.id}/follow/", {}, format='json')
		self.assertIn(follow.status_code, (200, 201), follow.data)

		feed = self.client.get('/api/activity/following?limit=50')
		self.assertEqual(feed.status_code, 200)
		self.assertTrue(isinstance(feed.data, list))
		# Should include activity about Romanisme (followed artist)
		self.assertTrue(any(a.get('target_name') == 'Romanisme' for a in feed.data))
		# Should exclude activity about Other Album
		self.assertFalse(any(a.get('target_name') == 'Other Album' for a in feed.data))

	def test_friends_activity_feed_only_friends(self):
		# Alex creates activity
		self._login('alex')
		rate_res = self.client.post(
			f"/api/albums/{self.album.id}/rate/",
			{"rating": 5},
			format='json',
		)
		self.assertIn(rate_res.status_code, (200, 201), rate_res.data)

		# Maria creates activity
		self.client.credentials()
		self._login('maria')
		review_res = self.client.post(
			f"/api/albums/{self.album.id}/reviews/",
			{"title": "", "content": "Nice"},
			format='json',
		)
		self.assertEqual(review_res.status_code, 201, review_res.data)

		# Viewer is friends only with Alex
		FriendRequest.objects.create(
			sender=self.viewer,
			receiver=self.alex,
			status=FriendRequest.Status.ACCEPTED,
		)

		self.client.credentials()
		self._login('viewer')
		res = self.client.get('/api/activity/friends?limit=20')
		self.assertEqual(res.status_code, 200)
		self.assertTrue(isinstance(res.data, list))
		self.assertTrue(any(a.get('actor_username') == 'alex' for a in res.data))
		self.assertFalse(any(a.get('actor_username') == 'maria' for a in res.data))
		self.assertFalse(any(a.get('actor_username') == 'viewer' for a in res.data))

	def test_notifications_incoming_friend_requests_and_review_likes(self):
		# Viewer writes a review
		self._login('viewer')
		review_res = self.client.post(
			f"/api/albums/{self.album.id}/reviews/",
			{"title": "", "content": "Nice"},
			format='json',
		)
		self.assertEqual(review_res.status_code, 201, review_res.data)
		review_id = review_res.data.get('id')
		self.assertTrue(review_id)

		# Maria likes viewer's review
		self.client.credentials()
		self._login('maria')
		like_res = self.client.post(f"/api/reviews/{review_id}/like/", {}, format='json')
		self.assertEqual(like_res.status_code, 200, like_res.data)
		self.assertEqual(like_res.data.get('liked'), True)

		# Alex sends friend request to viewer
		self.client.credentials()
		self._login('alex')
		fr_res = self.client.post(
			"/api/friends/request",
			{"receiver_username": "viewer"},
			format='json',
		)
		self.assertEqual(fr_res.status_code, 201, fr_res.data)
		self.assertEqual(fr_res.data.get('sender_username'), 'alex')
		self.assertEqual(fr_res.data.get('receiver_username'), 'viewer')
		self.assertEqual(fr_res.data.get('status'), 'pending')

		# Viewer checks notifications
		self.client.credentials()
		self._login('viewer')
		notifs = self.client.get('/api/notifications/?limit=20')
		self.assertEqual(notifs.status_code, 200)
		self.assertIn('incoming_friend_requests', notifs.data)
		self.assertIn('review_likes', notifs.data)
		self.assertTrue(any(fr.get('sender_username') == 'alex' for fr in notifs.data.get('incoming_friend_requests', [])))
		self.assertTrue(any(lk.get('liker_username') == 'maria' for lk in notifs.data.get('review_likes', [])))
		like_item = next((lk for lk in notifs.data.get('review_likes', []) if lk.get('liker_username') == 'maria'), None)
		self.assertTrue(like_item)
		self.assertEqual(like_item.get('review_id'), review_id)
		self.assertEqual(like_item.get('album_slug'), 'romanisme')

	def test_notifications_empty_for_new_user(self):
		self._login('viewer')
		res = self.client.get('/api/notifications/?limit=20')
		self.assertEqual(res.status_code, 200)
		self.assertEqual(res.data.get('incoming_friend_requests'), [])
		self.assertEqual(res.data.get('review_likes'), [])

	def test_notification_preferences_default_and_update(self):
		self._login('viewer')
		res = self.client.get('/api/notifications/preferences/')
		self.assertEqual(res.status_code, 200)
		self.assertEqual(res.data.get('digest_frequency'), 'off')
		self.assertEqual(res.data.get('digest_channel'), 'in_app')
		self.assertEqual(res.data.get('notify_friend_requests'), True)
		self.assertEqual(res.data.get('notify_review_likes'), True)
		self.assertEqual(res.data.get('notify_review_replies'), True)
		self.assertEqual(res.data.get('notify_mentions'), True)
		self.assertEqual(res.data.get('notify_artist_follows'), True)
		self.assertEqual(res.data.get('notify_followed_artist_releases'), True)
		self.assertEqual(res.data.get('notify_genre_releases'), True)
		self.assertEqual(res.data.get('notify_release_reminders'), True)
		self.assertEqual(res.data.get('release_reminder_days'), 3)
		self.assertEqual(res.data.get('notify_friends_activity'), True)

		patch = self.client.patch(
			'/api/notifications/preferences/',
			{
				'notify_review_likes': False,
				'digest_frequency': 'daily',
			},
			format='json',
		)
		self.assertEqual(patch.status_code, 200, patch.data)
		self.assertEqual(patch.data.get('notify_review_likes'), False)
		self.assertEqual(patch.data.get('digest_frequency'), 'daily')
		self.assertEqual(patch.data.get('notify_release_reminders'), True)
		self.assertEqual(patch.data.get('release_reminder_days'), 3)

		res2 = self.client.get('/api/notifications/preferences/')
		self.assertEqual(res2.status_code, 200)
		self.assertEqual(res2.data.get('notify_review_likes'), False)
		self.assertEqual(res2.data.get('digest_frequency'), 'daily')

	def test_notifications_respect_preferences(self):
		# Viewer writes a review
		self._login('viewer')
		review_res = self.client.post(
			f"/api/albums/{self.album.id}/reviews/",
			{"title": "", "content": "Nice"},
			format='json',
		)
		self.assertEqual(review_res.status_code, 201, review_res.data)
		review_id = review_res.data.get('id')
		self.assertTrue(review_id)

		# Maria likes viewer's review
		self.client.credentials()
		self._login('maria')
		like_res = self.client.post(f"/api/reviews/{review_id}/like/", {}, format='json')
		self.assertEqual(like_res.status_code, 200, like_res.data)
		self.assertEqual(like_res.data.get('liked'), True)

		# Alex sends friend request to viewer
		self.client.credentials()
		self._login('alex')
		fr_res = self.client.post(
			"/api/friends/request",
			{"receiver_username": "viewer"},
			format='json',
		)
		self.assertEqual(fr_res.status_code, 201, fr_res.data)

		# Viewer disables review-like notifications
		self.client.credentials()
		self._login('viewer')
		prefs_res = self.client.patch(
			'/api/notifications/preferences/',
			{'notify_review_likes': False},
			format='json',
		)
		self.assertEqual(prefs_res.status_code, 200)
		self.assertEqual(prefs_res.data.get('notify_review_likes'), False)

		notifs = self.client.get('/api/notifications/?limit=20')
		self.assertEqual(notifs.status_code, 200)
		self.assertTrue(any(fr.get('sender_username') == 'alex' for fr in notifs.data.get('incoming_friend_requests', [])))
		self.assertEqual(notifs.data.get('review_likes', []), [])

	def test_notifications_mentions_from_review_comment(self):
		# Alex writes a review
		self._login('alex')
		review_res = self.client.post(
			f"/api/albums/{self.album.id}/reviews/",
			{"title": "", "content": "Nice"},
			format='json',
		)
		self.assertEqual(review_res.status_code, 201, review_res.data)
		review_id = review_res.data.get('id')
		self.assertTrue(review_id)

		# Maria comments and mentions viewer
		self.client.credentials()
		self._login('maria')
		comment_res = self.client.post(
			f"/api/reviews/{review_id}/comments/",
			{"content": "Salut @viewer, ce zici?"},
			format='json',
		)
		self.assertEqual(comment_res.status_code, 201, comment_res.data)

		# Viewer sees mention notification
		self.client.credentials()
		self._login('viewer')
		notifs = self.client.get('/api/notifications/?limit=20')
		self.assertEqual(notifs.status_code, 200)
		self.assertIn('mentions', notifs.data)
		self.assertTrue(any(m.get('mentioner_username') == 'maria' for m in notifs.data.get('mentions', [])))
		mention_item = next((m for m in notifs.data.get('mentions', []) if m.get('mentioner_username') == 'maria'), None)
		self.assertTrue(mention_item)
		self.assertEqual(mention_item.get('review_id'), review_id)
		self.assertEqual(mention_item.get('album_slug'), 'romanisme')

	def test_notifications_mentions_respect_preferences(self):
		# Alex writes a review
		self._login('alex')
		review_res = self.client.post(
			f"/api/albums/{self.album.id}/reviews/",
			{"title": "", "content": "Nice"},
			format='json',
		)
		self.assertEqual(review_res.status_code, 201, review_res.data)
		review_id = review_res.data.get('id')
		self.assertTrue(review_id)

		# Viewer disables mention notifications
		self.client.credentials()
		self._login('viewer')
		prefs_res = self.client.patch(
			'/api/notifications/preferences/',
			{'notify_mentions': False},
			format='json',
		)
		self.assertEqual(prefs_res.status_code, 200)
		self.assertEqual(prefs_res.data.get('notify_mentions'), False)

		# Maria comments and mentions viewer
		self.client.credentials()
		self._login('maria')
		comment_res = self.client.post(
			f"/api/reviews/{review_id}/comments/",
			{"content": "Salut @viewer"},
			format='json',
		)
		self.assertEqual(comment_res.status_code, 201, comment_res.data)

		# Viewer should not see mention notification
		self.client.credentials()
		self._login('viewer')
		notifs = self.client.get('/api/notifications/?limit=20')
		self.assertEqual(notifs.status_code, 200)
		self.assertEqual(notifs.data.get('mentions', []), [])

	def test_notifications_digest_daily_includes_friends_activity(self):
		# Alex creates activity
		self._login('alex')
		rate_res = self.client.post(
			f"/api/albums/{self.album.id}/rate/",
			{"rating": 5},
			format='json',
		)
		self.assertIn(rate_res.status_code, (200, 201), rate_res.data)

		# Viewer is friends with Alex
		from interactions.models import FriendRequest
		FriendRequest.objects.create(
			sender=self.viewer,
			receiver=self.alex,
			status=FriendRequest.Status.ACCEPTED,
		)

		# Viewer enables daily digest and checks it
		self.client.credentials()
		self._login('viewer')
		prefs_res = self.client.patch(
			'/api/notifications/preferences/',
			{'digest_frequency': 'daily', 'notify_friends_activity': True},
			format='json',
		)
		self.assertEqual(prefs_res.status_code, 200)

		digest = self.client.get('/api/notifications/digest/?window=daily')
		self.assertEqual(digest.status_code, 200, digest.data)
		self.assertEqual(digest.data.get('enabled'), True)
		self.assertEqual(digest.data.get('window'), 'daily')
		self.assertIn('counts', digest.data)
		self.assertIn('friends_activity', digest.data)
		self.assertTrue(any(a.get('actor_username') == 'alex' for a in digest.data.get('friends_activity', [])))

	def test_notifications_include_artist_follows_and_releases(self):
		genre = Genre.objects.create(name='Hip-Hop', slug='hip-hop')
		self.album.genres.add(genre)

		# Viewer follows Puya.
		self._login('viewer')
		follow_viewer = self.client.post(f"/api/artists/{self.artist.id}/follow/", {}, format='json')
		self.assertIn(follow_viewer.status_code, (200, 201), follow_viewer.data)

		# Maria follows same artist to generate "follow" notification.
		self.client.credentials()
		self._login('maria')
		follow_maria = self.client.post(f"/api/artists/{self.artist.id}/follow/", {}, format='json')
		self.assertIn(follow_maria.status_code, (200, 201), follow_maria.data)

		# Viewer rates one album to infer preferred genre.
		self.client.credentials()
		self._login('viewer')
		rate = self.client.post(f"/api/albums/{self.album.id}/rate/", {"rating": 5}, format='json')
		self.assertIn(rate.status_code, (200, 201), rate.data)

		# New followed-artist release.
		followed_release = Album.objects.create(
			artist=self.artist,
			title='Nou Puya',
			slug='nou-puya',
			release_date=timezone.localdate(),
			is_approved=True,
		)
		followed_release.genres.add(genre)

		# New release in preferred genre from another artist.
		other_artist = Artist.objects.create(name='Other MC', slug='other-mc', is_approved=True)
		genre_release = Album.objects.create(
			artist=other_artist,
			title='Hip Hop Nou',
			slug='hip-hop-nou',
			release_date=timezone.localdate(),
			is_approved=True,
		)
		genre_release.genres.add(genre)

		notifs = self.client.get('/api/notifications/?limit=20')
		self.assertEqual(notifs.status_code, 200, notifs.data)
		self.assertIn('artist_follows', notifs.data)
		self.assertIn('followed_artist_releases', notifs.data)
		self.assertIn('preferred_genre_releases', notifs.data)

		self.assertTrue(any(x.get('follower_username') == 'maria' for x in notifs.data.get('artist_follows', [])))
		self.assertTrue(any(x.get('album_slug') == 'nou-puya' for x in notifs.data.get('followed_artist_releases', [])))
		self.assertTrue(any(x.get('album_slug') == 'hip-hop-nou' for x in notifs.data.get('preferred_genre_releases', [])))
		self.assertIn('upcoming_release_reminders', notifs.data)

	def test_release_calendar_personalized_with_reminders(self):
		genre = Genre.objects.create(name='Trap', slug='trap')
		self.album.genres.add(genre)

		self._login('viewer')
		follow_viewer = self.client.post(f"/api/artists/{self.artist.id}/follow/", {}, format='json')
		self.assertIn(follow_viewer.status_code, (200, 201), follow_viewer.data)
		rate = self.client.post(f"/api/albums/{self.album.id}/rate/", {"rating": 5}, format='json')
		self.assertIn(rate.status_code, (200, 201), rate.data)

		Album.objects.create(
			artist=self.artist,
			title='Urmeaza Curand',
			slug='urmeaza-curand',
			release_date=timezone.localdate() + timedelta(days=2),
			is_approved=True,
		)
		other_artist = Artist.objects.create(name='Trapster', slug='trapster', is_approved=True)
		genre_release = Album.objects.create(
			artist=other_artist,
			title='Trap Future',
			slug='trap-future',
			release_date=timezone.localdate() + timedelta(days=2),
			is_approved=True,
		)
		genre_release.genres.add(genre)

		res = self.client.get('/api/releases/calendar/?reminders_only=true&reminder_days=3')
		self.assertEqual(res.status_code, 200, res.data)
		self.assertIn('items', res.data)
		self.assertTrue(any(x.get('album_slug') == 'urmeaza-curand' for x in res.data.get('items', [])))
		self.assertTrue(any(x.get('album_slug') == 'trap-future' for x in res.data.get('items', [])))
		self.assertTrue(all(bool(x.get('is_reminder')) for x in res.data.get('items', [])))

	def test_activity_feed_empty_when_no_other_users_activity(self):
		# Viewer should get empty feed when only their own activity exists (feed excludes self).
		self._login('viewer')
		rate_res = self.client.post(
			f"/api/albums/{self.album.id}/rate/",
			{"rating": 5},
			format='json',
		)
		self.assertIn(rate_res.status_code, (200, 201), rate_res.data)
		res = self.client.get('/api/activity?limit=20')
		self.assertEqual(res.status_code, 200)
		self.assertEqual(res.data, [])

	def test_friends_activity_feed_empty_when_no_friends(self):
		self._login('viewer')
		res = self.client.get('/api/activity/friends?limit=20')
		self.assertEqual(res.status_code, 200)
		self.assertEqual(res.data, [])


class TestLiveStreamEndpoint(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"

		from django.contrib.auth import get_user_model
		User = get_user_model()
		self.user = User.objects.create_user(username='streamer', password=self.password)

		from music.models import Artist, Album
		from datetime import date
		self.artist = Artist.objects.create(name='Stream Artist', slug='stream-artist', is_approved=True)
		self.album = Album.objects.create(
			artist=self.artist,
			title='Stream Album',
			slug='stream-album',
			release_date=date(2020, 1, 1),
			is_approved=True,
		)

	def _login(self):
		login_res = self.client.post(
			"/api/auth/login/",
			{"username": self.user.username, "password": self.password},
			format="json",
		)
		self.assertEqual(login_res.status_code, 200, login_res.data)
		access = login_res.data.get("access")
		self.assertTrue(access)
		return access

	def test_activity_stream_emits_snapshot(self):
		access = self._login()
		response = self.client.get(
			f"/api/live/stream/?kind=activity&scope=all&limit=20&interval=2&token={access}",
		)
		self.assertEqual(response.status_code, 200, getattr(response, 'data', None))
		self.assertIn('text/event-stream', response.get('Content-Type', ''))

		first_chunk = next(iter(response.streaming_content)).decode('utf-8')
		self.assertIn('event: snapshot', first_chunk)
		data_line = next(line for line in first_chunk.splitlines() if line.startswith('data: '))
		payload = json.loads(data_line[6:])
		self.assertEqual(payload.get('kind'), 'activity')
		self.assertTrue(isinstance(payload.get('payload'), list))


class TestLevel3ProfileEdges(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = 'StrongPass123!'

		from django.contrib.auth import get_user_model
		User = get_user_model()
		self.user = User.objects.create_user(username='newbie', password=self.password)

	def _login(self):
		res = self.client.post(
			'/api/auth/login/',
			{'username': 'newbie', 'password': self.password},
			format='json',
		)
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get('access')
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

	def test_friends_list_empty_for_new_user(self):
		self._login()
		res = self.client.get('/api/friends/list')
		self.assertEqual(res.status_code, 200, res.data)
		self.assertEqual(res.data.get('friends'), [])
		self.assertEqual(res.data.get('incoming'), [])
		self.assertEqual(res.data.get('outgoing'), [])

	def test_profile_stats_empty_for_new_user(self):
		self._login()
		res = self.client.get('/api/profile/stats')
		self.assertEqual(res.status_code, 200, res.data)
		self.assertIn('favorite_albums', res.data)
		self.assertIn('favorite_songs', res.data)
		self.assertIn('favorite_genre', res.data)
		self.assertIn('favorite_artist', res.data)
		self.assertIn('total_ratings', res.data)
		self.assertIn('average_rating_given', res.data)
		self.assertIn('ratings_distribution', res.data)
		self.assertIn('top_genres_rated', res.data)
		self.assertIn('activity', res.data)
		self.assertEqual(res.data.get('total_ratings'), 0)
		self.assertTrue(isinstance(res.data.get('ratings_distribution'), list))
		self.assertTrue(isinstance(res.data.get('top_genres_rated'), list))
		self.assertTrue(isinstance(res.data.get('activity'), dict))
		self.assertTrue(isinstance(res.data.get('favorite_albums'), list))
		self.assertTrue(isinstance(res.data.get('favorite_songs'), list))
		self.assertEqual(len(res.data.get('favorite_albums')), 4)
		self.assertEqual(len(res.data.get('favorite_songs')), 4)
