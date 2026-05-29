from datetime import date

from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from interactions.models import AlbumRating
from music.models import Album, Artist
from users.models import UserPrivacySettings


User = get_user_model()


class TestPublicUserProfile(TestCase):
	def setUp(self):
		cache.clear()
		self.client = APIClient()
		self.password = "StrongPass123!"
		self.user = User.objects.create_user(username="alice", password=self.password)

	def test_public_profile_allow_any(self):
		res = self.client.get(f"/api/users/public/{self.user.username}")
		self.assertEqual(res.status_code, 200, getattr(res, 'data', None))
		self.assertIn("user_id", res.data)
		self.assertIn("username", res.data)
		self.assertIn("stats", res.data)
		self.assertIn("recent_reviews", res.data)
		self.assertIn("recent_album_ratings", res.data)
		self.assertIn("recent_activity", res.data)
		self.assertEqual(res.data.get("username"), "alice")
		self.assertTrue(isinstance(res.data.get("recent_reviews"), list))
		self.assertTrue(isinstance(res.data.get("recent_album_ratings"), list))
		self.assertTrue(isinstance(res.data.get("recent_activity"), list))


class TestUserSimilarity(TestCase):
	def setUp(self):
		cache.clear()
		self.client = APIClient()
		self.password = "StrongPass123!"

		self.user = User.objects.create_user(username="alice", password=self.password)
		self.user_b = User.objects.create_user(username="alex", password=self.password)
		self.user_c = User.objects.create_user(username="maria", password=self.password)

		artist = Artist.objects.create(name="A", slug="a", is_approved=True)
		self.album1 = Album.objects.create(artist=artist, title="One", slug="one", release_date=date(2020, 1, 1), is_approved=True)
		self.album2 = Album.objects.create(artist=artist, title="Two", slug="two", release_date=date(2020, 1, 2), is_approved=True)
		self.album3 = Album.objects.create(artist=artist, title="Three", slug="three", release_date=date(2020, 1, 3), is_approved=True)
		self.album4 = Album.objects.create(artist=artist, title="Four", slug="four", release_date=date(2020, 1, 4), is_approved=True)

	def _login_as(self, username: str):
		res = self.client.post("/api/auth/login/", {"username": username, "password": self.password}, format="json")
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get("access")
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_similar_users_orders_by_similarity(self):
		# alice rates 3 albums
		AlbumRating.objects.create(user=self.user, album=self.album1, rating=5)
		AlbumRating.objects.create(user=self.user, album=self.album2, rating=4)
		AlbumRating.objects.create(user=self.user, album=self.album3, rating=3)

		# alex overlaps on 2 of them (+ one extra)
		AlbumRating.objects.create(user=self.user_b, album=self.album1, rating=5)
		AlbumRating.objects.create(user=self.user_b, album=self.album2, rating=2)
		AlbumRating.objects.create(user=self.user_b, album=self.album4, rating=4)

		# maria overlaps on 1 of them
		AlbumRating.objects.create(user=self.user_c, album=self.album2, rating=5)

		self._login_as("alice")
		res = self.client.get("/api/users/similar")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))
		self.assertEqual([u["username"] for u in res.data], ["alex", "maria"])
		self.assertGreater(res.data[0]["similarity"], res.data[1]["similarity"])
		self.assertGreater(res.data[0]["similarity"], 0)
		# enriched fields
		self.assertEqual(res.data[0]["user_id"], self.user_b.id)
		self.assertEqual(res.data[0]["common_albums"], ["One"])
		self.assertEqual(res.data[0]["common_artists"], ["A"])
		self.assertEqual(res.data[0]["common_genres"], [])
		self.assertEqual(res.data[1]["user_id"], self.user_c.id)
		self.assertEqual(res.data[1]["common_albums"], ["Two"])
		self.assertEqual(res.data[1]["common_artists"], ["A"])
		self.assertEqual(res.data[1]["common_genres"], [])

	def test_compatibility_endpoint(self):
		AlbumRating.objects.create(user=self.user, album=self.album1, rating=5)
		AlbumRating.objects.create(user=self.user, album=self.album2, rating=4)
		AlbumRating.objects.create(user=self.user, album=self.album3, rating=3)

		AlbumRating.objects.create(user=self.user_b, album=self.album1, rating=5)
		AlbumRating.objects.create(user=self.user_b, album=self.album2, rating=2)

		self._login_as("alice")
		res = self.client.get(f"/api/users/{self.user_b.id}/compatibility")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertEqual(res.data["user_id"], self.user_b.id)
		self.assertEqual(res.data["username"], "alex")
		self.assertGreater(res.data["similarity"], 0)
		self.assertLessEqual(res.data["similarity"], 100)
		self.assertEqual(res.data["common_albums"], ["One"])
		self.assertEqual(res.data["common_artists"], ["A"])
		self.assertEqual(res.data["common_genres"], [])

	def test_similar_users_respect_compatibility_privacy(self):
		AlbumRating.objects.create(user=self.user, album=self.album1, rating=5)
		AlbumRating.objects.create(user=self.user_b, album=self.album1, rating=5)
		AlbumRating.objects.create(user=self.user_c, album=self.album1, rating=5)
		UserPrivacySettings.objects.create(user=self.user_c, public_compatibility=False)

		self._login_as("alice")
		res = self.client.get("/api/users/similar")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertEqual([u["username"] for u in res.data], ["alex"])

	def test_similar_users_empty_when_no_ratings(self):
		self._login_as("alice")
		res = self.client.get("/api/users/similar")
		self.assertEqual(res.status_code, 200)
		self.assertEqual(res.data, [])

	def test_user_search_requires_auth(self):
		res = self.client.get("/api/users/search", {"q": "al"})
		self.assertIn(res.status_code, (401, 403))

	def test_user_search_by_username_excludes_self(self):
		self._login_as("alice")
		res = self.client.get("/api/users/search", {"q": "al"})
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))
		usernames = [u["username"] for u in res.data]
		self.assertIn("alex", usernames)
		self.assertNotIn("alice", usernames)

	def test_user_search_empty_q_returns_empty_list(self):
		self._login_as("alice")
		res = self.client.get("/api/users/search", {"q": ""})
		self.assertEqual(res.status_code, 200)
		self.assertEqual(res.data, [])


class TestAuthThrottling(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"
		self.user = User.objects.create_user(username="alice", password=self.password)

	def test_login_is_throttled_after_limit(self):
		payload = {"username": self.user.username, "password": "wrong-password"}
		status_codes = []
		for _ in range(6):
			res = self.client.post("/api/auth/login/", payload, format="json")
			status_codes.append(res.status_code)
		self.assertEqual(status_codes[:5], [401, 401, 401, 401, 401])
		self.assertEqual(status_codes[5], 429)
		self.assertIn("detail", res.data)

	def test_register_is_throttled_after_limit(self):
		payload = {
			"username": "new-user",
			"email": "new-user@example.com",
			"password": "StrongPass123!",
		}
		status_codes = []
		for _ in range(4):
			res = self.client.post("/api/auth/register/", payload, format="json")
			status_codes.append(res.status_code)
		self.assertEqual(status_codes[:3], [201, 400, 400])
		self.assertEqual(status_codes[3], 429)
		self.assertIn("detail", res.data)
