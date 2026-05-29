#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from interactions.models import FriendRequest

User = get_user_model()

# Get Stefi8543 and Stefi8540
stefi8543 = User.objects.filter(username='Stefi8543').first()
stefi8540 = User.objects.filter(username='Stefi8540').first()

if stefi8543 and stefi8540:
    print(f"Stefi8543: {stefi8543.id}")
    print(f"Stefi8540: {stefi8540.id}")
    
    # Check all friend requests between them
    requests = FriendRequest.objects.filter(
        sender__in=[stefi8543, stefi8540],
        receiver__in=[stefi8543, stefi8540]
    )
    
    print(f"\nFriend requests between them: {requests.count()}")
    for fr in requests:
        print(f"  {fr.sender.username} → {fr.receiver.username}: {fr.status}")
    
    # Also check what getFriendsList would return for stefi8543
    print(f"\nChecking Stefi8543's friends list:")
    accepted = FriendRequest.objects.filter(
        sender=stefi8543,
        receiver=stefi8540,
        status=FriendRequest.Status.ACCEPTED
    ) | FriendRequest.objects.filter(
        sender=stefi8540,
        receiver=stefi8543,
        status=FriendRequest.Status.ACCEPTED
    )
    print(f"Accepted requests (correct enum): {accepted.count()}")
    for fr in accepted:
        print(f"  {fr.sender.username} → {fr.receiver.username}")
else:
    print("Users not found")
