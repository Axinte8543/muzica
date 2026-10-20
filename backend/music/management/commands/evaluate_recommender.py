from django.core.management.base import BaseCommand
from interactions.models import AlbumRating
from interactions.recommender import recommend_item_based_for_user
from music.views import _recommendations_payload
from collections import defaultdict


def precision_at_k(recs, truth_id, k):
    rec_ids = [int(r.get('album_id')) for r in recs[:k]]
    return 1.0 if int(truth_id) in rec_ids else 0.0


class Command(BaseCommand):
    help = 'Evaluate item-based recommender vs popularity baseline (leave-one-out)'

    def add_arguments(self, parser):
        parser.add_argument('--k', type=int, default=10, help='Precision@K')
        parser.add_argument('--max-users', type=int, default=0, help='Limit number of users to test (0 = all)')

    def handle(self, *args, **options):
        k = int(options.get('k') or 10)
        max_users = int(options.get('max_users') or 0)

        user_ids = (
            AlbumRating.objects.values_list('user_id', flat=True)
            .distinct()
            .order_by()
        )
        if max_users and max_users > 0:
            user_ids = user_ids[:max_users]

        total = 0
        hits_item = 0
        hits_pop = 0

                                    
        pop_rows = (
            AlbumRating.objects.values('album_id')
            .annotate(c=__import__('django.db.models').db.models.Count('album_id'))
            .order_by('-c')
        )
        popular_ids = [int(r['album_id']) for r in pop_rows]

        for uid in user_ids:
            ratings = list(AlbumRating.objects.filter(user_id=uid).order_by('created_at').values_list('album_id', 'created_at'))
            if len(ratings) < 2:
                continue
            total += 1
            test_album = int(ratings[-1][0])

                                           
            item_recs = recommend_item_based_for_user(int(uid), limit=k, exclude_albums=[test_album])
            hits_item += int(precision_at_k(item_recs, test_album, k))

                                                               
            user_rated = set(a for a, _ in ratings)
            pop_candidates = [aid for aid in popular_ids if aid not in user_rated]
            hits_pop += int(test_album in pop_candidates[:k])

        if total == 0:
            self.stdout.write('No users with enough ratings for evaluation')
            return

        self.stdout.write(f'Evaluated {total} users')
        self.stdout.write(f'Item-based Precision@{k}: {hits_item/total:.4f}')
        self.stdout.write(f'Popularity Precision@{k}: {hits_pop/total:.4f}')
