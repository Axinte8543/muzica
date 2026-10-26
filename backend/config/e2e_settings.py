"""Browser tests use a disposable database, supplied by e2e-server.mjs."""
import os
from .test_settings import *  # noqa: F403

DATABASES = {'default': {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': os.environ['E2E_DB_PATH'],
    'OPTIONS': {'timeout': 20, 'transaction_mode': 'IMMEDIATE'},
}}
CORS_ALLOWED_ORIGINS = ['http://127.0.0.1:5174']
REST_FRAMEWORK = {**REST_FRAMEWORK, 'DEFAULT_THROTTLE_CLASSES': ()}  # noqa: F405
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    key: '100000/min' for key in REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
}
