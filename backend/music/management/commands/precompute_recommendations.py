from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from interactions.models import AlbumRating
from interactions.recommender import compute_and_cache_user_recommendations
from interactions.recommender import compute_and_cache_neighbors


User = get_user_model()


class Command(BaseCommand):
    help = 'Precompute item-based recommendations for active users and store in cache.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=12, help='Number of recommendations to precompute per user')
        parser.add_argument('--max-users', type=int, default=0, help='Maximum number of users to process (0 = all)')

    def handle(self, *args, **options):
        limit = int(options.get('limit') or 12)
        max_users = int(options.get('max_users') or 0)

        user_ids = (
            AlbumRating.objects.values_list('user_id', flat=True)
            .distinct()
            .order_by()
        )
        if max_users and max_users > 0:
            user_ids = user_ids[:max_users]

        # Precompute global item neighbors once
        self.stdout.write('Computing item neighbors...')
        compute_and_cache_neighbors(k=50)

        count = 0
        for uid in user_ids:
            compute_and_cache_user_recommendations(int(uid), limit=limit)
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Precomputed recommendations for {count} users'))
