#!/usr/bin/env python
import os
import django
import json
from rest_framework.test import APIClient

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Get test user
stefi8543 = User.objects.get(username='Stefi8543')
stefi8540 = User.objects.get(username='Stefi8540')

# Create API client and authenticate
client = APIClient()
client.force_authenticate(user=stefi8543)

# Try to send a message
url = f'/api/chat/messages/{stefi8540.id}/'
data = {
    'recipient_id': stefi8540.id,
    'content': 'Test from API client',
    'reply_to_id': None,
}

response = client.post(url, data, format='json')
print(f"Status: {response.status_code}")
print(f"Response: {response.data}")
