#!/usr/bin/env python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

# Get test user
stefi8543 = User.objects.get(username='Stefi8543')
stefi8540 = User.objects.get(username='Stefi8540')

# Get token
refresh = RefreshToken.for_user(stefi8543)
access_token = str(refresh.access_token)

# Create HTTP client
client = Client()
headers = {'HTTP_AUTHORIZATION': f'Bearer {access_token}', 'CONTENT_TYPE': 'application/json'}

# Try to send a message
url = f'/api/chat/messages/{stefi8540.id}/'
data = {
    'content': 'Test from HTTP client',
}

import json
# Send JSON body and declare content type so Django test client doesn't try multipart encoding
response = client.post(url, data=json.dumps(data), content_type='application/json', **headers)

print(f"Status: {response.status_code}")
print(f"Response: {response.content.decode()}")
