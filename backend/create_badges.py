#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from interactions.models import Badge

badges_data = [
    {"code": "first_review", "name": "Critic activ", "description": "Scrie 2 review-uri", "category": "critic", "emoji": "🎬", "rarity": "common"},
    {"code": "decade_90s", "name": "Anni '90", "description": "Asculta 1 album lansat in 1990", "category": "explorer", "emoji": "📻", "rarity": "common"},
    {"code": "genre_explorer", "name": "Explorer de genuri", "description": "Asculta albumuri din 3 genuri diferite", "category": "explorer", "emoji": "🎵", "rarity": "uncommon"},
    {"code": "collector_10", "name": "Colectionist", "description": "Rateaza 10 albumuri", "category": "collector", "emoji": "⭐", "rarity": "uncommon"},
    {"code": "social_5friends", "name": "Sociabil", "description": "Adauga 5 prieteni", "category": "social", "emoji": "👥", "rarity": "uncommon"},
    {"code": "music_researcher", "name": "Cercetator", "description": "Urmareste 10 artisti", "category": "explorer", "emoji": "🔍", "rarity": "rare"},
    {"code": "devoted_listener", "name": "Ascultator devotat", "description": "Asculta 50 de albumuri", "category": "activity", "emoji": "🎧", "rarity": "rare"},
    {"code": "10_reviews", "name": "Critic incisiv", "description": "Scrie 10 review-uri", "category": "critic", "emoji": "✍️", "rarity": "rare"},
    {"code": "100_ratings", "name": "Mega Rater", "description": "Rateaza 100 de albumuri", "category": "milestone", "emoji": "💯", "rarity": "epic"},
]

for badge_data in badges_data:
    Badge.objects.get_or_create(code=badge_data['code'], defaults=badge_data)

print(f"✅ Created {Badge.objects.count()} badges")
