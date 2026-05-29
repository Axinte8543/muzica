#!/usr/bin/env python
import os
import django
import json
import urllib.request
import urllib.error

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()

# Get token for Stefi8543
stefi8543 = User.objects.get(username='Stefi8543')
refresh = RefreshToken.for_user(stefi8543)
access_token = str(refresh.access_token)

print(f"Access token: {access_token[:20]}...")

# Make POST request
url = 'http://127.0.0.1:8000/api/chat/messages/9/'
headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json',
}
data = {
    'recipient_id': 9,
    'content': 'Test message from script',
    'reply_to_id': None,
}

print(f"\nPOST {url}")
print(f"Data: {json.dumps(data, indent=2)}")

try:
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    response = urllib.request.urlopen(req)
    resp_data = json.loads(response.read())
    print(f"\nStatus: {response.status}")
    print(f"Response: {json.dumps(resp_data, indent=2, default=str)}")
except urllib.error.HTTPError as e:
    error_data = e.read()
    print(f"\nStatus: {e.code}")
    try:
        print(f"Error Response: {json.dumps(json.loads(error_data), indent=2, default=str)}")
    except:
        print(f"Error Response (raw): {error_data}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
