#!/usr/bin/env python
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from interactions.models import ChatMessage, SensitiveActionAudit
from interactions.serializers import ChatMessageSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

# Get users
stefi8543 = User.objects.get(username='Stefi8543')
stefi8540 = User.objects.get(username='Stefi8540')

# Create and serialize a test message
print("Creating message...")
msg = ChatMessage.objects.create(
    sender=stefi8543,
    recipient=stefi8540,
    content="Test from debug",
)
print(f"Message created: {msg.id}")

print("\nSerializing...")
try:
    serializer = ChatMessageSerializer(msg)
    print(f"Serialization OK: {json.dumps(serializer.data, indent=2, default=str)}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\nCalling _audit_sensitive_action...")
from interactions.views import _audit_sensitive_action

try:
    _audit_sensitive_action(
        actor=stefi8543,
        action_type=SensitiveActionAudit.ActionType.DM_SENT,
        target_type='chat_message',
        target_id=msg.id,
        summary='Direct message sent',
        metadata={'recipient_id': int(stefi8540.id), 'reply_to_id': None},
    )
    print("Audit call OK")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
