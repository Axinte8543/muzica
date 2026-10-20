from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from interactions.models import AlbumReview, MetadataSuggestion, ReviewComment
from music.models import Album, Artist, Song
from users.models import UserPrivacySettings


class TestModerationAndMetadataSuggestions(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"

		self.artist = Artist.objects.create(
		 name="Artist",
		 slug="artist",
		 is_approved=True,
		)
		self.album = Album.objects.create(
		 artist=self.artist,
		 title="Album",
		 slug="album",
		 release_date=date(2020, 1, 1),
		 cover_url="",
		 is_approved=True,
		)
		self.song = Song.objects.create(
		 album=self.album,
		 artist=self.artist,
		 title="Song",
		 slug="song",
		 track_number=1,
		 duration_seconds=123,
		 is_approved=True,
		)

		User = get_user_model()
		self.user = User.objects.create_user(username="alice", password=self.password, email="alice@example.com")
		self.staff = User.objects.create_user(username="mod", password=self.password, email="mod@example.com", is_staff=True)
		for user in (self.user, self.staff):
			UserPrivacySettings.objects.get_or_create(user=user, defaults={"email_verified": True})
			user.privacy.email_verified = True
			user.privacy.save(update_fields=["email_verified"])

		self.review = AlbumReview.objects.create(user=self.user, album=self.album, title="t", content="c")
		self.comment = ReviewComment.objects.create(user=self.user, review=self.review, content="hi")

	def _login(self, username: str):
		res = self.client.post(
		 "/api/auth/login/",
		 {"username": username, "password": self.password},
		 format="json",
		)
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get("access")
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_moderation_report_reason_code_and_queue(self):
		self._login("alice")

		create = self.client.post(
		 "/api/moderation/reports/",
		 {"target_type": "review", "target_id": self.review.id, "reason_code": "spam", "reason": "link spam"},
		 format="json",
		)
		self.assertEqual(create.status_code, 201, create.data)
		self.assertEqual(create.data.get("reason_code"), "spam")
		report_id = create.data.get("id")
		self.assertTrue(report_id)

		mine = self.client.get("/api/moderation/reports/?status=pending")
		self.assertEqual(mine.status_code, 200)
		self.assertTrue(any(r.get("id") == report_id for r in mine.data))

                                                  
		self.client.credentials()
		self._login("mod")

		queue = self.client.get("/api/moderation/reports/?status=pending&reason_code=spam")
		self.assertEqual(queue.status_code, 200)
		self.assertTrue(any(r.get("id") == report_id for r in queue.data))

		resolved = self.client.put(f"/api/moderation/reports/{report_id}/resolve/", {}, format="json")
		self.assertEqual(resolved.status_code, 200, resolved.data)
		self.assertEqual(resolved.data.get("status"), "resolved")
		self.assertTrue(resolved.data.get("resolution_reason"))
		self.assertTrue(resolved.data.get("resolution_feedback"))

	def test_metadata_suggestion_cover_and_tracklist_approval(self):
		self._login("alice")

		sugg = self.client.post(
		 "/api/moderation/suggestions/metadata/",
		 {
		  "target_type": "album",
		  "target_id": self.album.id,
		  "kind": "cover_url",
		  "payload": {"cover_url": "https://example.com/cover.jpg"},
		  "note": "missing cover",
		 },
		 format="json",
		)
		self.assertEqual(sugg.status_code, 201, sugg.data)
		suggestion_id = sugg.data.get("id")
		self.assertTrue(suggestion_id)
		self.assertEqual(sugg.data.get("status"), "pending")

		self.client.credentials()
		self._login("mod")

		approve = self.client.put(
		 f"/api/moderation/suggestions/metadata/{suggestion_id}/decision/",
		 {"action": "approve", "apply": True, "decision_note": "ok"},
		 format="json",
		)
		self.assertEqual(approve.status_code, 200, approve.data)
		self.assertEqual(approve.data.get("status"), "approved")
		self.assertEqual(approve.data.get("applied"), True)
		self.assertEqual(approve.data.get("target_name"), "Album")
		self.assertEqual(approve.data.get("target_slug"), "album")

		self.album.refresh_from_db()
		self.assertEqual(self.album.cover_url, "https://example.com/cover.jpg")

                                                  
                             
		self.client.credentials()
		self._login("alice")
		tracklist = self.client.post(
		 "/api/moderation/suggestions/metadata/",
		 {
		  "target_type": "album",
		  "target_id": self.album.id,
		  "kind": "tracklist",
		  "payload": {
		   "tracks": [
		    {"track_number": 1, "title": "Song", "duration_seconds": 123},
		    {"track_number": 2, "title": "New Track", "duration_seconds": 200},
		   ]
		  },
		 },
		 format="json",
		)
		self.assertEqual(tracklist.status_code, 201, tracklist.data)
		track_id = tracklist.data.get("id")
		self.assertTrue(track_id)

		self.client.credentials()
		self._login("mod")
		approve2 = self.client.put(
		 f"/api/moderation/suggestions/metadata/{track_id}/decision/",
		 {"action": "approve", "apply": True},
		 format="json",
		)
		self.assertEqual(approve2.status_code, 200, approve2.data)
		self.assertEqual(approve2.data.get("applied"), True)

                             
		self.assertTrue(Song.objects.filter(album=self.album, track_number=2, title="New Track", is_approved=True).exists())

	def test_metadata_suggestion_rejection_is_visible_to_suggester(self):
		self._login("alice")
		sugg = self.client.post(
		 "/api/moderation/suggestions/metadata/",
		 {
		  "target_type": "album",
		  "target_id": self.album.id,
		  "kind": "description",
		  "payload": {"description": "new text"},
		  "note": "please update",
		 },
		 format="json",
		)
		self.assertEqual(sugg.status_code, 201, sugg.data)
		suggestion_id = sugg.data.get("id")
		self.assertEqual(sugg.data.get("target_name"), "Album")

		self.client.credentials()
		self._login("mod")
		reject = self.client.put(
		 f"/api/moderation/suggestions/metadata/{suggestion_id}/decision/",
		 {"action": "reject", "decision_note": "Nu este potrivit."},
		 format="json",
		)
		self.assertEqual(reject.status_code, 200, reject.data)
		self.assertEqual(reject.data.get("status"), "rejected")
		self.assertEqual(reject.data.get("decision_note"), "Nu este potrivit.")

		self.client.credentials()
		self._login("alice")
		mine = self.client.get("/api/moderation/suggestions/metadata/?status=rejected")
		self.assertEqual(mine.status_code, 200, mine.data)
		item = next((x for x in mine.data if x.get("id") == suggestion_id), None)
		self.assertTrue(item)
		self.assertEqual(item.get("status"), "rejected")
		self.assertEqual(item.get("decision_note"), "Nu este potrivit.")
		self.assertEqual(item.get("target_name"), "Album")

	def test_review_comment_edit_history_public_endpoint(self):
		self._login("alice")
		old = self.comment.content
		res = self.client.put(
		 f"/api/review-comments/{self.comment.id}/",
		 {"content": "edited"},
		 format="json",
		)
		self.assertEqual(res.status_code, 200, res.data)

		history = self.client.get(f"/api/review-comments/{self.comment.id}/history/")
		self.assertEqual(history.status_code, 200)
		self.assertEqual(len(history.data), 1)
		self.assertEqual(history.data[0].get('previous_content'), old)

	def test_album_changelog_created_on_apply(self):
		self._login("alice")
		sugg = self.client.post(
		 "/api/moderation/suggestions/metadata/",
		 {
		  "target_type": "album",
		  "target_id": self.album.id,
		  "kind": "cover_url",
		  "payload": {"cover_url": "https://example.com/new.jpg"},
		 },
		 format="json",
		)
		self.assertEqual(sugg.status_code, 201, sugg.data)
		suggestion_id = sugg.data.get('id')
		self.assertTrue(suggestion_id)

		self.client.credentials()
		self._login("mod")
		approve = self.client.put(
		 f"/api/moderation/suggestions/metadata/{suggestion_id}/decision/",
		 {"action": "approve", "apply": True},
		 format="json",
		)
		self.assertEqual(approve.status_code, 200, approve.data)
		self.assertEqual(approve.data.get('applied'), True)

		changelog = self.client.get("/api/albums/album/changelog/")
		self.assertEqual(changelog.status_code, 200)
		self.assertTrue(len(changelog.data) >= 1)
		self.assertTrue(any(e.get('kind') == 'cover_url' for e in changelog.data))

	def test_contributor_badge_unlocked_after_approved_suggestions(self):
		for _ in range(5):
			MetadataSuggestion.objects.create(
			 suggester=self.user,
			 album=self.album,
			 kind=MetadataSuggestion.Kind.COVER_URL,
			 payload={'cover_url': 'x'},
			 status=MetadataSuggestion.Status.APPROVED,
			)
		self._login("alice")
		stats = self.client.get("/api/profile/stats/")
		self.assertEqual(stats.status_code, 200)
		badges = stats.data.get('badges') or []
		contrib = next((b for b in badges if b.get('key') == 'contributor_5'), None)
		self.assertIsNotNone(contrib)
		self.assertEqual(contrib.get('unlocked'), True)

	def test_metadata_suggestion_artist_image_url_apply(self):
		self._login("alice")
		sugg = self.client.post(
		 "/api/moderation/suggestions/metadata/",
		 {
		  "target_type": "artist",
		  "target_id": self.artist.id,
		  "kind": "image_url",
		  "payload": {"image_url": "https://example.com/artist.jpg"},
		 },
		 format="json",
		)
		self.assertEqual(sugg.status_code, 201, sugg.data)
		suggestion_id = sugg.data.get("id")
		self.assertTrue(suggestion_id)

		self.client.credentials()
		self._login("mod")
		approve = self.client.put(
		 f"/api/moderation/suggestions/metadata/{suggestion_id}/decision/",
		 {"action": "approve", "apply": True},
		 format="json",
		)
		self.assertEqual(approve.status_code, 200, approve.data)
		self.assertEqual(approve.data.get("applied"), True)

		self.artist.refresh_from_db()
		self.assertEqual(self.artist.image_url, "https://example.com/artist.jpg")
