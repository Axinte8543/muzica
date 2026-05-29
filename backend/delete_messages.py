#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from interactions.models import ChatMessage
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()
user1 = User.objects.get(id=5)  # Stefi8543
user2 = User.objects.get(id=9)  # Stefi8540

# Check remaining messages
remaining = ChatMessage.objects.filter(
    Q(sender=user1, recipient=user2) | Q(sender=user2, recipient=user1)
)

print(f"Mesaje rămase între {user1.username} și {user2.username}: {remaining.count()}")
for msg in remaining:
    print(f"  ID: {msg.id}, From: {msg.sender.username}, Content: {msg.content}, Created: {msg.created_at}")

# Delete all remaining
if remaining.exists():
    deleted_count, _ = remaining.delete()
    print(f"\n✓ Au fost șterse {deleted_count} mesaje rămase")
    
# Verify
final_count = ChatMessage.objects.filter(
    Q(sender=user1, recipient=user2) | Q(sender=user2, recipient=user1)
).count()
print(f"✓ Mesaje finale: {final_count}")
