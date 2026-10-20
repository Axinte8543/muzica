from django.core.management.base import BaseCommand
from django.db import transaction

from interactions.management.commands.seed_demo_activity import (
    COMMENT_TEXTS,
    REVIEW_TEXTS,
)
from interactions.models import AlbumReview, ReviewComment


OLD_REVIEW_CONTENT = (
    "Mi-a placut directia albumului, productia si felul in care se leaga piesele. "
    "Revin la cateva track-uri si dupa prima ascultare."
)
OLD_COMMENT_CONTENT = (
    "Bun punct, si mie mi-a ramas albumul in minte dupa ascultare."
)


class Command(BaseCommand):
    help = "Înlocuiește textele repetitive din datele demonstrative cu variante naturale."

    @transaction.atomic
    def handle(self, *args, **options):
        reviews = list(
            AlbumReview.objects.select_related("album")
            .filter(title__icontains="demo")
            .order_by("id")
        )
        for index, review in enumerate(reviews):
            title, content = REVIEW_TEXTS[(review.id + index) % len(REVIEW_TEXTS)]
            review.title = title
            if review.content == OLD_REVIEW_CONTENT:
                review.content = content
            review.save(update_fields=["title", "content", "updated_at"])

        comments = list(
            ReviewComment.objects.filter(content=OLD_COMMENT_CONTENT).order_by("id")
        )
        for index, comment in enumerate(comments):
            comment.content = COMMENT_TEXTS[(comment.id + index) % len(COMMENT_TEXTS)]
            comment.save(update_fields=["content", "updated_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Actualizate: {len(reviews)} review-uri și {len(comments)} comentarii."
            )
        )
