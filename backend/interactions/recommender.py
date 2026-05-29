from collections import defaultdict
from math import sqrt
from typing import Dict, List, Tuple

from django.core.cache import cache

from .models import AlbumRating
from music.models import Album


def _build_item_users() -> Dict[int, Dict[int, int]]:
    """Build sparse item->(user->rating) mapping."""
    rows = AlbumRating.objects.select_related('user').values_list('album_id', 'user_id', 'rating')
    item_users: Dict[int, Dict[int, int]] = {}
    for album_id, user_id, rating in rows:
        item_users.setdefault(int(album_id), {})[int(user_id)] = int(rating)
    return item_users


def _compute_topk_item_neighbors(k: int = 50) -> Dict[int, List[Tuple[int, float]]]:
    """Compute top-k cosine neighbors for each item using sparse vectors.

    Returns mapping item_id -> list of (neighbor_item_id, similarity)
    """
    item_users = _build_item_users()
    # precompute norms
    norms: Dict[int, float] = {}
    user_items: Dict[int, List[int]] = defaultdict(list)
    for item_id, users in item_users.items():
        s = 0.0
        for r in users.values():
            s += (float(r) ** 2)
        norms[item_id] = sqrt(s) if s > 0 else 0.0
        for uid in users:
            user_items[uid].append(item_id)

    neighbors: Dict[int, Dict[int, float]] = defaultdict(dict)

    # accumulate dot products by walking users' item lists
    for uid, items in user_items.items():
        for i in items:
            ri = item_users[i].get(uid, 0)
            for j in items:
                if i == j:
                    continue
                rj = item_users[j].get(uid, 0)
                neighbors[i].setdefault(j, 0.0)
                neighbors[i][j] += float(ri) * float(rj)

    topk: Dict[int, List[Tuple[int, float]]] = {}
    for i, sims in neighbors.items():
        ni = norms.get(i, 0.0)
        lst: List[Tuple[int, float]] = []
        for j, dot in sims.items():
            nj = norms.get(j, 0.0)
            if ni <= 0 or nj <= 0:
                continue
            cos = max(0.0, min(dot / (ni * nj), 1.0))
            if cos > 0:
                lst.append((j, cos))
        lst.sort(key=lambda x: -x[1])
        topk[i] = lst[:k]
    return topk


def compute_and_cache_neighbors(k: int = 50):
    """Compute neighbors and persist them in cache for reuse."""
    topk = _compute_topk_item_neighbors(k=k)
    # cache indefinitely (depends on cache backend persistence)
    cache.set('recommender:item_neighbors', topk, None)
    return topk


def recommend_item_based_for_user(user_id: int, limit: int = 20, neighbor_k: int = 50, exclude_albums: List[int] | None = None) -> List[dict]:
    """Compute simple item-based recommendations for `user_id` and return lightweight payloads.

    Results are cached by this function when precomputed via management command.
    """
    # Load precomputed neighbors from cache if present, else compute on the fly.
    cache_key_neighbors = 'recommender:item_neighbors'
    neighbors = cache.get(cache_key_neighbors)
    if neighbors is None:
        neighbors = _compute_topk_item_neighbors(k=neighbor_k)
        # cache neighbors for a while; in production use Redis with proper TTL
        cache.set(cache_key_neighbors, neighbors, 60 * 60)

    qs = AlbumRating.objects.filter(user_id=user_id)
    if exclude_albums:
        qs = qs.exclude(album_id__in=exclude_albums)
    user_ratings = qs.values_list('album_id', 'rating')
    rated = {int(a): int(r) for a, r in user_ratings}
    if not rated:
        return []

    scores: Dict[int, float] = {}
    weight_sum: Dict[int, float] = {}

    for album_id, rating in rated.items():
        neighs = neighbors.get(album_id, [])
        for nid, sim in neighs:
            if int(nid) in rated:
                continue
            scores.setdefault(nid, 0.0)
            weight_sum.setdefault(nid, 0.0)
            w = sim
            scores[nid] += w * (float(rating) / 5.0)
            weight_sum[nid] += w

    final: List[Tuple[int, float]] = []
    for nid, sc in scores.items():
        ws = weight_sum.get(nid, 1.0)
        final_score = sc / ws if ws > 0 else sc
        final.append((nid, final_score))

    final.sort(key=lambda x: -x[1])
    album_ids = [a for a, _ in final[:limit]]
    albums = Album.objects.filter(id__in=album_ids).select_related('artist')
    album_by_id = {int(a.id): a for a in albums}
    results: List[dict] = []
    for aid, score in final[:limit]:
        a = album_by_id.get(int(aid))
        if not a:
            continue
        results.append({
            'album': a.title,
            'artist': a.artist.name,
            'album_id': a.id,
            'album_slug': a.slug,
            'cover_url': a.cover_url or '',
            'score': round(float(score), 2),
        })
    return results


def compute_and_cache_user_recommendations(user_id: int, limit: int = 12) -> None:
    recs = recommend_item_based_for_user(user_id, limit=limit)
    cache_key = f'recommendations:user:item:{user_id}'
    cache.set(cache_key, recs, 60 * 60 * 6)  # 6 hours


def invalidate_user_recommendations(user_id: int) -> None:
    cache.delete(f'recommendations:user:item:{int(user_id)}')
