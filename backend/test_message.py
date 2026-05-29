#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from interactions.models import ChatMessage
from interactions.serializers import ChatMessageSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

# Get users
stefi8543 = User.objects.get(username='Stefi8543')
stefi8540 = User.objects.get(username='Stefi8540')

# Create a test message
msg = ChatMessage.objects.create(
    sender=stefi8543,
    recipient=stefi8540,
    content="Test message",
)

print(f"Created message: {msg.id}")

# Try to serialize it
try:
    serializer = ChatMessageSerializer(msg)
    print(f"Serialized successfully:")
    print(serializer.data)
except Exception as e:
    print(f"Serialization error: {e}")
    import traceback
    traceback.print_exc()
