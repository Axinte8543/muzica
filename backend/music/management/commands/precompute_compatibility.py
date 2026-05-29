from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from interactions.models import AlbumLike, AlbumListen, AlbumRating, AlbumReview, FavoriteAlbum
from interactions.similarity import compute_and_cache_similar_users


User = get_user_model()


class Command(BaseCommand):
	help = 'Precompute compatibility rankings for users and store them in cache.'

	def add_arguments(self, parser):
		parser.add_argument('--limit', type=int, default=50, help='Number of similar users to cache per profile')
		parser.add_argument('--max-users', type=int, default=0, help='Maximum number of users to process (0 = all)')

	def handle(self, *args, **options):
		limit = int(options.get('limit') or 50)
		max_users = int(options.get('max_users') or 0)

		user_ids = set()
		for model in (AlbumRating, AlbumLike, AlbumListen, FavoriteAlbum, AlbumReview):
			user_ids.update(model.objects.values_list('user_id', flat=True).distinct())

		ordered_user_ids = sorted(int(uid) for uid in user_ids if uid is not None)
		if max_users and max_users > 0:
			ordered_user_ids = ordered_user_ids[:max_users]

		count = 0
		for user_id in ordered_user_ids:
			compute_and_cache_similar_users(int(user_id), limit=limit)
			count += 1

		self.stdout.write(self.style.SUCCESS(f'Precomputed compatibility for {count} users'))