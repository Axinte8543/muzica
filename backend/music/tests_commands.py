from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from django.contrib.auth import get_user_model
from interactions.models import AlbumRating
from music.models import Album, Artist


User = get_user_model()


class TestRecommenderManagementCommands(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mc", password="pw")
        self.other = User.objects.create_user(username="other", password="pw")

        self.artist = Artist.objects.create(name="A", slug="a", is_approved=True)
        self.album1 = Album.objects.create(artist=self.artist, title="One", slug="one", release_date="2020-01-01", is_approved=True)
        self.album2 = Album.objects.create(artist=self.artist, title="Two", slug="two", release_date="2020-01-02", is_approved=True)

                                                    
        AlbumRating.objects.create(user=self.user, album=self.album1, rating=5)
        AlbumRating.objects.create(user=self.other, album=self.album1, rating=4)
        AlbumRating.objects.create(user=self.other, album=self.album2, rating=5)

    def tearDown(self):
        cache.clear()

    def test_precompute_recommendations_command_creates_cache(self):
        out = StringIO()
                                           
        call_command('precompute_recommendations', limit=5, max_users=0, stdout=out)
        output = out.getvalue()
        self.assertIn('Computing item neighbors', output)
                                                               
                                                
        self.assertTrue(cache.get(f'recommendations:user:item:{self.user.id}') is not None or cache.get(f'recommendations:user:item:{self.other.id}') is not None)

    def test_evaluate_recommender_command_runs_and_prints(self):
        out = StringIO()
                                                     
        call_command('evaluate_recommender', k=5, max_users=1, stdout=out)
        output = out.getvalue()
                                                            
        self.assertTrue('Evaluated' in output or 'No users' in output)
