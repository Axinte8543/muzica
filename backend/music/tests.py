from config.test_helpers import verify_fixture_emails
from datetime import date

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from interactions.models import AlbumListen, AlbumRating, ArtistFollow, ArtistRating, FavoriteAlbum, FriendRequest, List, ListLike, ReviewComment, SongRating, UserActivity
from interactions.models import AlbumReview
from interactions.recommender import compute_and_cache_user_recommendations
from music.models import Album, Artist, ArtistSimilarity, Genre, Song, SongFeature


User = get_user_model()


class TestRecommendations(TestCase):
	def setUp(self):
		cache.clear()
		self.addCleanup(cache.clear)
		self.client = APIClient()
		self.password = "StrongPass123!"
		self.user = User.objects.create_user(username="alice", password=self.password)
		self.other = User.objects.create_user(username="bob", password=self.password)

		self.rock = Genre.objects.create(name="Rock", slug="rock")
		self.jazz = Genre.objects.create(name="Jazz", slug="jazz")

		self.artist_a = Artist.objects.create(name="Artist A", slug="artist-a", is_approved=True)
		self.artist_b = Artist.objects.create(name="Artist B", slug="artist-b", is_approved=True)
		self.artist_c = Artist.objects.create(name="Artist C", slug="artist-c", is_approved=True)

                                              
		self.seed_album = Album.objects.create(
		 artist=self.artist_a,
		 title="Seed",
		 slug="seed",
		 release_date=date(2020, 1, 1),
		 is_approved=True,
		)
		self.seed_album.genres.add(self.rock)

              
		self.both_match = Album.objects.create(
		 artist=self.artist_b,
		 title="Both",
		 slug="both",
		 release_date=date(2020, 1, 2),
		 is_approved=True,
		)
		self.both_match.genres.add(self.rock)

		self.genre_only = Album.objects.create(
		 artist=self.artist_c,
		 title="GenreOnly",
		 slug="genre-only",
		 release_date=date(2020, 1, 3),
		 is_approved=True,
		)
		self.genre_only.genres.add(self.rock)

		self.artist_only = Album.objects.create(
		 artist=self.artist_b,
		 title="ArtistOnly",
		 slug="artist-only",
		 release_date=date(2020, 1, 4),
		 is_approved=True,
		)
		self.artist_only.genres.add(self.jazz)

	def _login(self):
		verify_fixture_emails()
		res = self.client.post("/api/auth/login/", {"username": "alice", "password": self.password}, format="json")
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get("access")
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_recommendations_require_auth(self):
		res = self.client.get("/api/recommendations/")
		self.assertIn(res.status_code, (401, 403))

	def test_recommendations_score_and_order(self):
                                   
		AlbumRating.objects.create(user=self.user, album=self.seed_album, rating=5)
                   
		ArtistFollow.objects.create(user=self.user, artist=self.artist_b)

                                                            
		AlbumRating.objects.create(user=self.other, album=self.both_match, rating=5)
		AlbumRating.objects.create(user=self.other, album=self.genre_only, rating=5)
		AlbumRating.objects.create(user=self.other, album=self.artist_only, rating=5)

		self._login()
		res = self.client.get("/api/recommendations/?limit=10")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))
                                                        
		self.assertFalse(any(r.get("album") == "Seed" for r in res.data))
                                               
		self.assertEqual(res.data[0].get("album"), "Both")
		self.assertEqual(res.data[0].get("artist"), "Artist B")
		self.assertEqual(res.data[0].get("album_slug"), "both")
		self.assertEqual(res.data[0].get("artist_slug"), "artist-b")
		self.assertEqual(res.data[0].get("album_id"), self.both_match.id)
		self.assertIn("cover_url", res.data[0])
		self.assertIn("reason", res.data[0])
		self.assertTrue(bool(str(res.data[0].get("reason") or "").strip()))
		self.assertIn("genre_score", res.data[0])
		self.assertIn("similar_users_score", res.data[0])
		self.assertIn("popularity_score", res.data[0])
		self.assertGreaterEqual(res.data[0].get("score", 0), 0.5)
                                                
		self.assertTrue(any(r.get("album") == "GenreOnly" for r in res.data))
		self.assertTrue(any(r.get("album") == "ArtistOnly" for r in res.data))

	def test_recommendations_empty_for_new_user(self):
                                                          
		self._login()
		res = self.client.get("/api/recommendations/?limit=10")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertEqual(res.data, [])

	def test_recommendations_use_listens_and_favorites(self):
		AlbumListen.objects.create(user=self.user, album=self.seed_album, listened_date=date(2025, 1, 1))
		FavoriteAlbum.objects.create(user=self.user, album=self.seed_album, position=FavoriteAlbum.Position.ONE)

		self._login()
		res = self.client.get("/api/recommendations/?limit=10")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))
		self.assertTrue(res.data)
		self.assertFalse(any(r.get("album") == "Seed" for r in res.data))
		self.assertTrue(any(r.get("album_slug") in {"both", "genre-only"} for r in res.data))

	def test_recommendations_use_user_activity_feed(self):
		UserActivity.objects.create(
		 actor=self.user,
		 activity_type=UserActivity.Type.LISTEN_ALBUM,
		 target_id=self.seed_album.id,
		 target_name=self.seed_album.title,
		)
		UserActivity.objects.create(
		 actor=self.user,
		 activity_type=UserActivity.Type.FOLLOW_ARTIST,
		 target_id=self.artist_b.id,
		 target_name=self.artist_b.name,
		)

		self._login()
		res = self.client.get("/api/recommendations/?limit=10")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))
		self.assertTrue(res.data)
		self.assertTrue(any(r.get("artist_slug") == "artist-b" for r in res.data))

	def test_recommendation_cache_is_invalidated_on_rating_change(self):
		AlbumRating.objects.create(user=self.user, album=self.seed_album, rating=5)
		compute_and_cache_user_recommendations(self.user.id, limit=10)
		cache_key = f"recommendations:user:item:{self.user.id}"
		self.assertIsNotNone(cache.get(cache_key))

		self._login()
		res = self.client.post(f"/api/albums/{self.both_match.id}/rate", {"rating": 4}, format="json")
		self.assertIn(res.status_code, (200, 201), res.data)
		self.assertIsNone(cache.get(cache_key))

	def test_recommendation_cache_is_invalidated_on_follow(self):
		AlbumRating.objects.create(user=self.user, album=self.seed_album, rating=5)
		compute_and_cache_user_recommendations(self.user.id, limit=10)
		cache_key = f"recommendations:user:item:{self.user.id}"
		self.assertIsNotNone(cache.get(cache_key))

		self._login()
		res = self.client.post(f"/api/artists/{self.artist_b.id}/follow", {}, format="json")
		self.assertIn(res.status_code, (200, 201), res.data)
		self.assertIsNone(cache.get(cache_key))

	def test_recommendations_use_similar_users_ratings(self):
                                                
		AlbumRating.objects.create(user=self.user, album=self.seed_album, rating=5)
                                                                
		AlbumRating.objects.create(user=self.other, album=self.seed_album, rating=5)
                                                  
		AlbumRating.objects.create(user=self.other, album=self.genre_only, rating=5)
		AlbumRating.objects.create(user=self.other, album=self.artist_only, rating=1)

		self._login()
		res = self.client.get("/api/recommendations/?limit=10")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))

                                                                  
                                                                             
		slugs = [r.get("album_slug") for r in res.data]
		self.assertIn("genre-only", slugs)
		self.assertIn("artist-only", slugs)
		self.assertLess(slugs.index("genre-only"), slugs.index("artist-only"))


class TestAlbumDetailFeaturedArtists(TestCase):
	def setUp(self):
		self.client = APIClient()

		self.artist_main = Artist.objects.create(name='Main', slug='main', is_approved=True)
		self.artist_feat = Artist.objects.create(name='Feat', slug='feat', is_approved=True)
		self.album = Album.objects.create(
		 artist=self.artist_main,
		 title='Album',
		 slug='album',
		 release_date=date(2020, 1, 1),
		 is_approved=True,
		)
		self.song = Song.objects.create(
		 album=self.album,
		 artist=self.artist_main,
		 title='Track',
		 slug='track',
		 track_number=1,
		 duration_seconds=120,
		 is_approved=True,
		)

	def test_album_detail_returns_featured_artists_on_songs(self):
		SongFeature.objects.create(song=self.song, artist=self.artist_feat)

		res = self.client.get('/api/albums/album/')
		self.assertEqual(res.status_code, 200, res.data)
		songs = res.data.get('songs')
		self.assertTrue(isinstance(songs, list))
		self.assertEqual(len(songs), 1)
		featured = songs[0].get('featured_artists')
		self.assertTrue(isinstance(featured, list))
		self.assertEqual(len(featured), 1)
		self.assertEqual(featured[0].get('slug'), 'feat')
		self.assertEqual(featured[0].get('name'), 'Feat')

	def test_album_detail_returns_empty_featured_artists_when_none(self):
		res = self.client.get('/api/albums/album/')
		self.assertEqual(res.status_code, 200, res.data)
		songs = res.data.get('songs')
		self.assertTrue(isinstance(songs, list))
		self.assertEqual(len(songs), 1)
		self.assertEqual(songs[0].get('featured_artists'), [])


class TestAlbumGenreFilters(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.artist = Artist.objects.create(name="Genre Artist", slug="genre-artist", is_approved=True)
		self.album = Album.objects.create(
		 artist=self.artist,
		 title="Genre Album",
		 slug="genre-album",
		 release_date=date(2024, 1, 1),
		 is_approved=True,
		)
		self.genre = Genre.objects.create(name="Latin Rock", slug="latin-rock")
		self.artist.genres.add(self.genre)
		for index in range(2):
			Song.objects.create(album=self.album, artist=self.artist, title=f'Track {index}', slug=f'genre-track-{index}', track_number=index+1)

	def test_album_filters_include_artist_genres(self):
		res = self.client.get("/api/albums/filters/")
		self.assertEqual(res.status_code, 200, res.data)
		genres = res.data.get("genres", [])
		slugs = [g.get("slug") for g in genres]
		self.assertIn("latin-rock", slugs)

	def test_album_list_filters_by_artist_genre(self):
		res = self.client.get("/api/albums/?genre=latin-rock")
		self.assertEqual(res.status_code, 200, res.data)
		results = res.data.get("results", [])
		slugs = [a.get("slug") for a in results]
		self.assertIn("genre-album", slugs)


class TestAlbumExtrasEndpoints(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"
		self.user = User.objects.create_user(username="alice", password=self.password)
		self.other = User.objects.create_user(username="bob", password=self.password)

		self.rock = Genre.objects.create(name="Rock", slug="rock")
		self.artist = Artist.objects.create(name="Artist", slug="artist", is_approved=True)
		self.album = Album.objects.create(
		 artist=self.artist,
		 title="Album",
		 slug="album-extras",
		 release_date=date(2020, 1, 1),
		 is_approved=True,
		)
		self.album.genres.add(self.rock)

		self.song1 = Song.objects.create(
		 album=self.album,
		 artist=self.artist,
		 title="Track 1",
		 slug="track-1",
		 track_number=1,
		 duration_seconds=120,
		 is_approved=True,
		)

	def _login(self):
		verify_fixture_emails()
		res = self.client.post(
		 "/api/auth/login/",
		 {"username": "alice", "password": self.password},
		 format="json",
		)
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get("access")
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_album_detail_includes_comments_count(self):
		review = AlbumReview.objects.create(user=self.user, album=self.album, content="Nice")
		ReviewComment.objects.create(user=self.user, review=review, content="c1")
		ReviewComment.objects.create(user=self.other, review=review, content="c2")

		res = self.client.get("/api/albums/album-extras/")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertEqual(res.data.get("comments_count"), 2)

	def test_album_comments_endpoint_lists_recent_comments(self):
		review = AlbumReview.objects.create(user=self.user, album=self.album, content="Nice")
		ReviewComment.objects.create(user=self.user, review=review, content="c1")
		ReviewComment.objects.create(user=self.other, review=review, content="c2")

		res = self.client.get("/api/albums/album-extras/comments/?limit=10")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))
		self.assertEqual(len(res.data), 2)
		self.assertIn("content", res.data[0])
		self.assertIn("user_username", res.data[0])

	def test_album_detail_includes_song_my_rating_when_authed(self):
		SongRating.objects.create(user=self.user, song=self.song1, rating=4)
		self._login()
		res = self.client.get("/api/albums/album-extras/")
		self.assertEqual(res.status_code, 200, res.data)
		songs = res.data.get("songs")
		self.assertTrue(isinstance(songs, list))
		self.assertEqual(len(songs), 1)
		self.assertEqual(songs[0].get("my_rating"), 4)

	def test_album_recommendations_endpoint_returns_similar_by_genre(self):
		other_album = Album.objects.create(
		 artist=self.artist,
		 title="Other",
		 slug="other",
		 release_date=date(2020, 1, 2),
		 is_approved=True,
		)
		other_album.genres.add(self.rock)

		res = self.client.get("/api/albums/album-extras/recommendations/?limit=10")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))
		self.assertTrue(any(a.get("slug") == "other" for a in res.data))

	def test_album_recommendations_endpoint_returns_similar_by_collaborators(self):
                                               
		artist_feat = Artist.objects.create(name='Feat', slug='feat', is_approved=True)
		SongFeature.objects.create(song=self.song1, artist=artist_feat)

                                                                      
		artist_other = Artist.objects.create(name='OtherArtist', slug='other-artist', is_approved=True)
		album2 = Album.objects.create(
		 artist=artist_other,
		 title='Collab Match',
		 slug='collab-match',
		 release_date=date(2020, 2, 1),
		 is_approved=True,
		)
		Song.objects.create(
		 album=album2,
		 artist=artist_other,
		 title='T2',
		 slug='t2',
		 track_number=1,
		 duration_seconds=120,
		 is_approved=True,
		)
		SongFeature.objects.create(song=Song.objects.get(slug='t2'), artist=artist_feat)

                                                              
		res = self.client.get("/api/albums/album-extras/recommendations/?limit=20")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))
		self.assertTrue(any(a.get('slug') == 'collab-match' for a in res.data))

	def test_album_public_lists_endpoint_returns_lists_containing_album(self):
		lst = List.objects.create(user=self.other, name="Public list", is_public=True)
		lst.albums.add(self.album)
		ListLike.objects.create(user=self.user, list=lst)

		res = self.client.get("/api/albums/album-extras/user-lists/?limit=10")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))
		self.assertEqual(len(res.data), 1)
		self.assertEqual(res.data[0].get("name"), "Public list")
		self.assertEqual(res.data[0].get("likes_count"), 1)


class TestArtistCommunityEndpoints(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"
		self.user = User.objects.create_user(username="alice", password=self.password)
		self.other = User.objects.create_user(username="bob", password=self.password)

		self.artist = Artist.objects.create(name="Artist", slug="artist", is_approved=True)
		self.other_artist = Artist.objects.create(name="Other", slug="other", is_approved=True)

		self.album_main = Album.objects.create(
		 artist=self.artist,
		 title="Main Album",
		 slug="main-album",
		 release_date=date(2020, 1, 1),
		 is_approved=True,
		 mb_primary_type="album",
		 mb_secondary_types="",
		)
		self.single_main = Album.objects.create(
		 artist=self.artist,
		 title="Main Single",
		 slug="main-single",
		 release_date=date(2020, 1, 2),
		 is_approved=True,
		 mb_primary_type="single",
		 mb_secondary_types="",
		)
		self.inferred_single = Album.objects.create(
		 artist=self.artist,
		 title="Inferred Single",
		 slug="inferred-single",
		 release_date=date(2020, 1, 2),
		 is_approved=True,
		 mb_primary_type="",
		 mb_secondary_types="",
		)
		self.ep_main = Album.objects.create(
		 artist=self.artist,
		 title="Main EP",
		 slug="main-ep",
		 release_date=date(2020, 1, 3),
		 is_approved=True,
		 mb_primary_type="ep",
		 mb_secondary_types="",
		)
		self.comp_main = Album.objects.create(
		 artist=self.artist,
		 title="Main Compilation",
		 slug="main-comp",
		 release_date=date(2020, 1, 4),
		 is_approved=True,
		 mb_primary_type="compilation",
		 mb_secondary_types="",
		)

		self.song_a = Song.objects.create(
		 album=self.album_main,
		 artist=self.artist,
		 title="Song A",
		 slug="song-a",
		 track_number=1,
		 duration_seconds=120,
		 is_approved=True,
		)
		Song.objects.create(
		 album=self.inferred_single,
		 artist=self.artist,
		 title="Only Track",
		 slug="only-track",
		 track_number=1,
		 duration_seconds=120,
		 is_approved=True,
		)
		self.song_b = Song.objects.create(
		 album=self.album_main,
		 artist=self.artist,
		 title="Song B",
		 slug="song-b",
		 track_number=2,
		 duration_seconds=120,
		 is_approved=True,
		)

		self.other_album = Album.objects.create(
		 artist=self.other_artist,
		 title="Other Album",
		 slug="other-album",
		 release_date=date(2020, 2, 1),
		 is_approved=True,
		 mb_primary_type="album",
		 mb_secondary_types="",
		)
		self.other_song = Song.objects.create(
		 album=self.other_album,
		 artist=self.other_artist,
		 title="Other Song (feat Artist)",
		 slug="other-song-feat",
		 track_number=1,
		 duration_seconds=120,
		 is_approved=True,
		)
		SongFeature.objects.create(song=self.other_song, artist=self.artist)

	def test_artist_detail_includes_followers_count(self):
		ArtistFollow.objects.create(user=self.user, artist=self.artist)
		res = self.client.get('/api/artists/artist/')
		self.assertEqual(res.status_code, 200, res.data)
		self.assertEqual(res.data.get('followers_count'), 1)

	def test_artist_discography_endpoint_groups(self):
		res = self.client.get('/api/artists/artist/discography/?limit=50')
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data.get('albums'), list))
		self.assertTrue(isinstance(res.data.get('singles'), list))
                                                               
                                                             
		self.assertTrue(isinstance(res.data.get('appears_on'), list))
		self.assertEqual(len(res.data.get('albums')), 3)
		self.assertEqual(len(res.data.get('singles')), 2)
		self.assertEqual(len(res.data.get('appears_on')), 1)
		self.assertEqual(res.data['albums'][0].get('mb_primary_type'), 'album')
		single_slugs = [a.get('slug') for a in (res.data.get('singles') or [])]
		self.assertIn('main-single', single_slugs)
		self.assertIn('inferred-single', single_slugs)

	def test_artist_similar_artists_endpoint(self):
		third = Artist.objects.create(name="Third", slug="third", is_approved=True)
		ArtistSimilarity.objects.create(from_artist=self.artist, to_artist=self.other_artist, match=0.9, source='test')
		ArtistSimilarity.objects.create(from_artist=self.artist, to_artist=third, match=0.5, source='test')

		res = self.client.get('/api/artists/artist/similar-artists/?limit=10')
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))
		self.assertGreaterEqual(len(res.data), 2)
		self.assertIn('match', res.data[0])
		self.assertEqual(res.data[0].get('slug'), 'other')

	def test_artist_top_songs_endpoint_returns_scores(self):
		SongRating.objects.create(user=self.user, song=self.song_a, rating=5)
		SongRating.objects.create(user=self.other, song=self.song_a, rating=5)
		SongRating.objects.create(user=self.user, song=self.song_b, rating=1)

		res = self.client.get('/api/artists/artist/top-songs/?limit=10')
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))
		self.assertGreaterEqual(len(res.data), 2)
		self.assertEqual(res.data[0].get('slug'), 'song-a')
		self.assertIn('average_rating', res.data[0])
		self.assertIn('ratings_count', res.data[0])


class TestTopArtistsEndpoint(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.user1 = User.objects.create_user(username="u1", password="StrongPass123!")
		self.user2 = User.objects.create_user(username="u2", password="StrongPass123!")

		self.artist_a = Artist.objects.create(name="Artist A", slug="artist-a", is_approved=True)
		self.artist_b = Artist.objects.create(name="Artist B", slug="artist-b", is_approved=True)
		self.artist_c = Artist.objects.create(name="Artist C", slug="artist-c", is_approved=True)
		self.artist_d = Artist.objects.create(name="Artist D", slug="artist-d", is_approved=True)

		self.album_a_approved = Album.objects.create(
		 artist=self.artist_a,
		 title="A Approved",
		 slug="a-approved",
		 release_date=date(2020, 1, 1),
		 is_approved=True,
		)
		self.album_a_unapproved = Album.objects.create(
		 artist=self.artist_a,
		 title="A Unapproved",
		 slug="a-unapproved",
		 release_date=date(2020, 1, 2),
		 is_approved=False,
		)

		self.album_b = Album.objects.create(
		 artist=self.artist_b,
		 title="B",
		 slug="b",
		 release_date=date(2020, 2, 1),
		 is_approved=True,
		)
		self.album_d = Album.objects.create(
		 artist=self.artist_d,
		 title="D",
		 slug="d",
		 release_date=date(2020, 3, 1),
		 is_approved=True,
		)

                                                     
		ArtistRating.objects.create(user=self.user1, artist=self.artist_a, rating=5)
		ArtistRating.objects.create(user=self.user2, artist=self.artist_a, rating=5)
		AlbumRating.objects.create(user=self.user1, album=self.album_a_unapproved, rating=1)

                              
		ArtistRating.objects.create(user=self.user1, artist=self.artist_b, rating=4)
		ArtistRating.objects.create(user=self.user2, artist=self.artist_b, rating=5)

                                                                                          
		ArtistRating.objects.create(user=self.user1, artist=self.artist_d, rating=5)

	def test_top_artists_orders_and_filters(self):
		res = self.client.get("/api/top-artists/?page_size=50")
		self.assertEqual(res.status_code, 200, getattr(res, 'data', None))
		self.assertTrue(isinstance(res.data, dict))
		self.assertIn("results", res.data)

		items = res.data["results"]
		slugs = [a.get("slug") for a in items]
		self.assertIn("artist-a", slugs)
		self.assertIn("artist-b", slugs)
		self.assertIn("artist-d", slugs)
                              
		self.assertNotIn("artist-c", slugs)

                                                             
		self.assertEqual(slugs[0], "artist-a")
		self.assertEqual(slugs[1], "artist-d")
		self.assertEqual(slugs[2], "artist-b")

		artist_a_payload = next(a for a in items if a.get("slug") == "artist-a")
		self.assertAlmostEqual(artist_a_payload.get("average_rating"), 5.0, places=4)
		self.assertEqual(artist_a_payload.get("ratings_count"), 2)
		self.assertEqual(artist_a_payload.get("albums_count"), 1)


class TestRandomArtistEndpoint(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.approved1 = Artist.objects.create(name="Approved 1", slug="approved-1", is_approved=True)
		self.approved2 = Artist.objects.create(name="Approved 2", slug="approved-2", is_approved=True)
		Artist.objects.create(name="Unapproved", slug="unapproved", is_approved=False)

	def test_random_artist_returns_approved_artist(self):
		res = self.client.get('/api/artists/random/')
		self.assertEqual(res.status_code, 200, getattr(res, 'data', None))
		self.assertIn(res.data.get('slug'), {'approved-1', 'approved-2'})
		self.assertIn('name', res.data)
		self.assertIn('id', res.data)


class TestPlatformStats(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.user = User.objects.create_user(username="u1", password="StrongPass123!")
		self.user2 = User.objects.create_user(username="u2", password="StrongPass123!")

		self.hiphop = Genre.objects.create(name="Hip-Hop", slug="hip-hop")
		self.rap = Genre.objects.create(name="Rap", slug="rap")
		self.pop = Genre.objects.create(name="Pop", slug="pop")

		self.artist_a = Artist.objects.create(name="Puya", slug="puya", is_approved=True)
		self.artist_b = Artist.objects.create(name="Guess Who", slug="guess-who", is_approved=True)

		self.album_a1 = Album.objects.create(
		 artist=self.artist_a,
		 title="Romanisme",
		 slug="romanisme",
		 release_date=date(2020, 1, 1),
		 is_approved=True,
		)
		self.album_a1.genres.add(self.hiphop, self.rap)

		self.album_a2 = Album.objects.create(
		 artist=self.artist_a,
		 title="Puya Album",
		 slug="puya-album",
		 release_date=date(2020, 1, 2),
		 is_approved=True,
		)
		self.album_a2.genres.add(self.rap)

		self.album_b1 = Album.objects.create(
		 artist=self.artist_b,
		 title="Balade pentru urechea ta",
		 slug="balade",
		 release_date=date(2020, 1, 3),
		 is_approved=True,
		)
		self.album_b1.genres.add(self.pop)

	def test_stats_payload(self):
            
                                                           
                                 
                                 
		AlbumRating.objects.create(user=self.user, album=self.album_a1, rating=5)
		AlbumRating.objects.create(user=self.user2, album=self.album_a1, rating=4)
		AlbumRating.objects.create(user=self.user, album=self.album_a2, rating=5)
		AlbumRating.objects.create(user=self.user2, album=self.album_b1, rating=3)

                                          
		AlbumReview.objects.create(user=self.user, album=self.album_a1, title="t1", content="c")
		AlbumReview.objects.create(user=self.user2, album=self.album_a1, title="t2", content="c")
		AlbumReview.objects.create(user=self.user, album=self.album_a1, title="t3", content="c")
		AlbumReview.objects.create(user=self.user, album=self.album_b1, title="t4", content="c")

		res = self.client.get("/api/stats")
		self.assertEqual(res.status_code, 200, getattr(res, 'data', None))
		self.assertIn("top_genres", res.data)
		self.assertIn("top_artists", res.data)
		self.assertIn("top_albums", res.data)

                                            
                                                      
		genres = res.data["top_genres"]
		self.assertEqual([g["name"] for g in genres[:3]], ["Rap", "Hip-Hop", "Pop"])
		by_name = {g["name"]: g for g in genres}
		self.assertEqual(by_name["Rap"]["ratings"], 3)
		self.assertEqual(by_name["Rap"]["percent"], 50)
		self.assertEqual(by_name["Hip-Hop"]["ratings"], 2)
		self.assertEqual(by_name["Hip-Hop"]["percent"], 33)
		self.assertEqual(by_name["Pop"]["ratings"], 1)
		self.assertEqual(by_name["Pop"]["percent"], 17)

		artists = res.data["top_artists"]
		self.assertEqual(artists[0]["name"], "Puya")
		self.assertEqual(artists[0]["ratings"], 3)
		self.assertEqual(artists[1]["name"], "Guess Who")
		self.assertEqual(artists[1]["ratings"], 1)

		albums = res.data["top_albums"]
		self.assertEqual(albums[0]["title"], "Romanisme")
		self.assertEqual(albums[0]["reviews"], 3)
		self.assertEqual(albums[1]["title"], "Balade pentru urechea ta")
		self.assertEqual(albums[1]["reviews"], 1)

	def test_stats_empty_when_no_data(self):
		res = self.client.get("/api/stats")
		self.assertEqual(res.status_code, 200, getattr(res, 'data', None))
		self.assertIn("top_genres", res.data)
		self.assertIn("top_artists", res.data)
		self.assertIn("top_albums", res.data)
		self.assertEqual(res.data.get("top_genres"), [])
		self.assertEqual(res.data.get("top_artists"), [])
		self.assertEqual(res.data.get("top_albums"), [])


class TestHome(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.password = "StrongPass123!"

		self.alice = User.objects.create_user(username="alice", password=self.password)
		self.bob = User.objects.create_user(username="bob", password=self.password)
		self.carl = User.objects.create_user(username="carl", password=self.password)

		self.artist = Artist.objects.create(name="Puya", slug="puya", is_approved=True)
		self.album = Album.objects.create(
		 artist=self.artist,
		 title="Romanisme",
		 slug="romanisme",
		 release_date=date(2020, 1, 1),
		 is_approved=True,
		)
		AlbumRating.objects.create(user=self.bob, album=self.album, rating=5)

	def _login(self, username: str):
		verify_fixture_emails()
		res = self.client.post(
		 "/api/auth/login/",
		 {"username": username, "password": self.password},
		 format="json",
		)
		self.assertEqual(res.status_code, 200, res.data)
		access = res.data.get("access")
		self.assertTrue(access)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

	def test_home_unauth_payload_shape(self):
		res = self.client.get("/api/home")
		self.assertEqual(res.status_code, 200)
		self.assertIn("recommendations", res.data)
		self.assertIn("friends_recommendations", res.data)
		self.assertIn("friends_activity", res.data)
		self.assertIn("popular_albums", res.data)
		self.assertIn("new_releases", res.data)
		self.assertIn("trending_albums", res.data)
		self.assertIn("trending_artists", res.data)
		self.assertIn("most_discussed_albums", res.data)
		self.assertTrue(isinstance(res.data.get("recommendations"), list))
		self.assertTrue(isinstance(res.data.get("friends_recommendations"), list))
		self.assertTrue(isinstance(res.data.get("friends_activity"), list))
		self.assertTrue(isinstance(res.data.get("popular_albums"), list))
		self.assertTrue(isinstance(res.data.get("new_releases"), list))
		self.assertTrue(isinstance(res.data.get("trending_albums"), list))
		self.assertTrue(isinstance(res.data.get("trending_artists"), list))
		self.assertTrue(isinstance(res.data.get("most_discussed_albums"), list))
		self.assertEqual(res.data.get("recommendations"), [])
		self.assertEqual(res.data.get("friends_recommendations"), [])
		self.assertEqual(res.data.get("friends_activity"), [])

	def test_home_discovery_sections_return_items_with_recent_activity(self):
		now = timezone.now()

		listen = AlbumListen.objects.create(user=self.alice, album=self.album)
		AlbumListen.objects.filter(pk=listen.pk).update(
		 listened_at=now,
		 listened_date=now.date(),
		)

		review = AlbumReview.objects.create(user=self.alice, album=self.album, title='t', content='c')
		AlbumReview.objects.filter(pk=review.pk).update(created_at=now)
		comment = ReviewComment.objects.create(user=self.bob, review=review, content='c1')
		ReviewComment.objects.filter(pk=comment.pk).update(created_at=now)

		res = self.client.get("/api/home")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(any(a.get('slug') == 'romanisme' for a in res.data.get('trending_albums') or []))
		self.assertTrue(any(a.get('slug') == 'puya' for a in res.data.get('trending_artists') or []))
		self.assertTrue(any(a.get('slug') == 'romanisme' for a in res.data.get('most_discussed_albums') or []))

	def test_home_friends_activity_only_friends(self):
                              
		FriendRequest.objects.create(
		 sender=self.alice,
		 receiver=self.bob,
		 status=FriendRequest.Status.ACCEPTED,
		)

                                        
		UserActivity.objects.create(
		 actor=self.bob,
		 activity_type=UserActivity.Type.RATE_ALBUM,
		 target_id=self.album.id,
		 target_name=self.album.title,
		 rating=5,
		)
                                   
		UserActivity.objects.create(
		 actor=self.carl,
		 activity_type=UserActivity.Type.RATE_ALBUM,
		 target_id=self.album.id,
		 target_name=self.album.title,
		 rating=4,
		)

		self._login("alice")
		res = self.client.get("/api/home")
		self.assertEqual(res.status_code, 200, res.data)

		acts = res.data.get("friends_activity")
		self.assertTrue(isinstance(acts, list))
		self.assertTrue(any(a.get('actor_username') == 'bob' for a in acts))
		self.assertFalse(any(a.get('actor_username') == 'carl' for a in acts))

	def test_home_friends_recommendations_include_friend_likes(self):
		FriendRequest.objects.create(
		 sender=self.alice,
		 receiver=self.bob,
		 status=FriendRequest.Status.ACCEPTED,
		)

		self._login("alice")
		res = self.client.get("/api/home")
		self.assertEqual(res.status_code, 200, res.data)
		recs = res.data.get("friends_recommendations")
		self.assertTrue(isinstance(recs, list))
		self.assertTrue(any(r.get("album_slug") == "romanisme" for r in recs))
		first = next((r for r in recs if r.get("album_slug") == "romanisme"), None)
		self.assertTrue(first)
		reason = str(first.get("reason") or "")
		self.assertIn("bob", reason.lower())
		self.assertTrue(any(ch.isdigit() for ch in reason))

	def test_home_auth_new_user_has_empty_personal_sections(self):
                                                             
		self._login("alice")
		res = self.client.get("/api/home")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertIn("recommendations", res.data)
		self.assertIn("friends_recommendations", res.data)
		self.assertIn("friends_activity", res.data)
		self.assertTrue(isinstance(res.data.get("recommendations"), list))
		self.assertTrue(isinstance(res.data.get("friends_recommendations"), list))
		self.assertTrue(isinstance(res.data.get("friends_activity"), list))
		self.assertEqual(res.data.get("recommendations"), [])
		self.assertEqual(res.data.get("friends_recommendations"), [])
		self.assertEqual(res.data.get("friends_activity"), [])

	def test_friends_recommendations_endpoint_require_auth(self):
		res = self.client.get("/api/recommendations/friends/")
		self.assertIn(res.status_code, (401, 403))

	def test_friends_recommendations_endpoint_returns_data(self):
		FriendRequest.objects.create(
		 sender=self.alice,
		 receiver=self.bob,
		 status=FriendRequest.Status.ACCEPTED,
		)

		self._login("alice")
		res = self.client.get("/api/recommendations/friends/?limit=10")
		self.assertEqual(res.status_code, 200, res.data)
		self.assertTrue(isinstance(res.data, list))
		self.assertTrue(any(r.get("album_slug") == "romanisme" for r in res.data))


class TestAlbumFilteringByPickMode(TestCase):
                                                            
 
	def setUp(self):
		self.client = APIClient()
		self.artist = Artist.objects.create(name="Test Artist", slug="test-artist", is_approved=True)
  
                                                                  
		self.album_no_songs = Album.objects.create(
		 artist=self.artist,
		 title="Album No Songs",
		 slug="album-no-songs",
		 release_date=date(2020, 1, 1),
		 is_approved=True,
		)
  
                              
		self.single = Album.objects.create(
		 artist=self.artist,
		 title="Single Track",
		 slug="single-track",
		 release_date=date(2020, 1, 2),
		 is_approved=True,
		)
		Song.objects.create(
		 album=self.single,
		 artist=self.artist,
		 title="Single Song",
		 slug="single-song",
		 track_number=1,
		 duration_seconds=180,
		 is_approved=True,
		)
  
                                    
		self.album_2tracks = Album.objects.create(
		 artist=self.artist,
		 title="Album Two Tracks",
		 slug="album-2tracks",
		 release_date=date(2020, 1, 3),
		 is_approved=True,
		)
		Song.objects.create(
		 album=self.album_2tracks,
		 artist=self.artist,
		 title="Track 1",
		 slug="track-1",
		 track_number=1,
		 duration_seconds=180,
		 is_approved=True,
		)
		Song.objects.create(
		 album=self.album_2tracks,
		 artist=self.artist,
		 title="Track 2",
		 slug="track-2",
		 track_number=2,
		 duration_seconds=200,
		 is_approved=True,
		)
  
                      
		self.album_5tracks = Album.objects.create(
		 artist=self.artist,
		 title="Album Five Tracks",
		 slug="album-5tracks",
		 release_date=date(2020, 1, 4),
		 is_approved=True,
		)
		for i in range(1, 6):
			Song.objects.create(
			 album=self.album_5tracks,
			 artist=self.artist,
			 title=f"Track {i}",
			 slug=f"5track-track-{i}",
			 track_number=i,
			 duration_seconds=180,
			 is_approved=True,
			)
 
	def test_album_list_without_pick_mode_returns_albums_only(self):
                                                               
		res = self.client.get("/api/albums/")
		self.assertEqual(res.status_code, 200, res.data)
		results = res.data.get("results", [])
		slugs = [a.get("slug") for a in results]
  
		self.assertNotIn("single-track", slugs)
		self.assertNotIn("album-no-songs", slugs)
		self.assertIn("album-2tracks", slugs)
		self.assertIn("album-5tracks", slugs)

	def test_album_list_with_singles_filter_returns_singles_only(self):
		res = self.client.get("/api/albums/?release_type=singles")
		self.assertEqual(res.status_code, 200, res.data)
		results = res.data.get("results", [])
		slugs = [a.get("slug") for a in results]

		self.assertIn("single-track", slugs)
		self.assertNotIn("album-2tracks", slugs)
		self.assertNotIn("album-5tracks", slugs)
		self.assertNotIn("album-no-songs", slugs)
		self.assertEqual(results[0].get("release_type"), "single")
 
	def test_album_list_with_pick_mode_song_returns_all(self):
                                                                   
		res = self.client.get("/api/albums/?pickMode=song")
		self.assertEqual(res.status_code, 200, res.data)
		results = res.data.get("results", [])
		slugs = [a.get("slug") for a in results]
  
		self.assertIn("single-track", slugs)
		self.assertIn("album-2tracks", slugs)
		self.assertIn("album-5tracks", slugs)
		self.assertNotIn("album-no-songs", slugs)
 
	def test_album_list_with_pick_mode_album_excludes_singles(self):
                                                                         
		res = self.client.get("/api/albums/?pickMode=album")
		self.assertEqual(res.status_code, 200, res.data)
		results = res.data.get("results", [])
		slugs = [a.get("slug") for a in results]
  
                                          
		self.assertNotIn("single-track", slugs)
		self.assertNotIn("album-no-songs", slugs)
  
                                     
		self.assertIn("album-2tracks", slugs)
		self.assertIn("album-5tracks", slugs)
 
	def test_album_list_pick_mode_album_respects_other_filters(self):
                                                                         
                      
		rock = Genre.objects.create(name="Rock", slug="rock")
		self.album_2tracks.genres.add(rock)
  
		res = self.client.get("/api/albums/?pickMode=album&genre=rock")
		self.assertEqual(res.status_code, 200, res.data)
		results = res.data.get("results", [])
		slugs = [a.get("slug") for a in results]
  
                                                    
		self.assertIn("album-2tracks", slugs)
                                          
		self.assertNotIn("single-track", slugs)
