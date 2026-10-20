from datetime import timedelta
from pathlib import Path

from decouple import Csv, config
import os
import logging


def _env(name: str, default: str = '') -> str:
    return os.environ.get(name, default)


def _safe_bool(value) -> bool:
    normalized = str(value).strip().lower()
    if normalized in {'1', 'true', 't', 'yes', 'y', 'on', 'debug', 'dev', 'development'}:
        return True
    if normalized in {'0', 'false', 'f', 'no', 'n', 'off', 'release', 'prod', 'production', ''}:
        return False
    logging.warning("Invalid boolean value %r; defaulting to False", value)
    return False


def _load_azure_key_vault_secrets() -> None:
    vault_url = _env('AZURE_KEY_VAULT_URL').strip()
    if not vault_url:
        return
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
    except Exception:
        logging.warning('Azure Key Vault integration requested but azure SDKs are not installed')
        return

    try:
        client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())
        secret_names = [
            'SECRET_KEY',
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'SENTRY_DSN',
        ]
        for secret_name in secret_names:
            if not _env(secret_name).strip():
                try:
                    secret_value = client.get_secret(secret_name).value
                    if secret_value:
                        os.environ[secret_name] = secret_value
                except Exception:
                    logging.exception('Failed to hydrate secret %s from Azure Key Vault', secret_name)
    except Exception:
        logging.exception('Azure Key Vault bootstrap failed')


_load_azure_key_vault_secrets()


BASE_DIR = Path(__file__).resolve().parent.parent



SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me')
DEBUG = config('DEBUG', default=False, cast=_safe_bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())



INSTALLED_APPS = [
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'monitoring',
    'users',
    'music',
    'interactions',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'config.security.SecurityHeadersMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'monitoring.middleware.PrometheusMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


DB_ENGINE = config('DB_ENGINE', default='sqlite')

if DB_ENGINE.lower() in {'postgres', 'postgresql'}:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='licenta_music_db'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }



AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]



LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True




STATIC_URL = 'static/'

SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=not DEBUG, cast=bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=not DEBUG, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=not DEBUG, cast=bool)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = config('SECURE_REFERRER_POLICY', default='strict-origin-when-cross-origin')
X_FRAME_OPTIONS = 'DENY'

SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=not DEBUG, cast=bool)
SESSION_COOKIE_HTTPONLY = config('SESSION_COOKIE_HTTPONLY', default=True, cast=bool)
SESSION_COOKIE_SAMESITE = config('SESSION_COOKIE_SAMESITE', default='Strict' if not DEBUG else 'Lax')
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=not DEBUG, cast=bool)
CSRF_COOKIE_HTTPONLY = config('CSRF_COOKIE_HTTPONLY', default=True, cast=bool)
CSRF_COOKIE_SAMESITE = config('CSRF_COOKIE_SAMESITE', default='Strict' if not DEBUG else 'Lax')


def _csv_env(name: str) -> list[str]:
    return [value.strip() for value in config(name, default='', cast=Csv()) if str(value).strip()]


CSP_STYLE_SRC_EXTRA = _csv_env('CSP_STYLE_SRC_EXTRA')
CSP_SCRIPT_SRC_EXTRA = _csv_env('CSP_SCRIPT_SRC_EXTRA')
CSP_CONNECT_SRC_EXTRA = _csv_env('CSP_CONNECT_SRC_EXTRA')
CSP_IMG_SRC_EXTRA = _csv_env('CSP_IMG_SRC_EXTRA')
CSP_FONT_SRC_EXTRA = _csv_env('CSP_FONT_SRC_EXTRA')
CSP_FRAME_SRC_EXTRA = _csv_env('CSP_FRAME_SRC_EXTRA')

DEFAULT_CSP_DIRECTIVES = {
    'default-src': ["'self'"],
    'base-uri': ["'self'"],
    'frame-ancestors': ["'none'"],
    'object-src': ["'none'"],
    'img-src': ["'self'", 'data:', 'blob:'] + CSP_IMG_SRC_EXTRA,
    'font-src': ["'self'", 'data:'] + CSP_FONT_SRC_EXTRA,
    'style-src': ["'self'"] + ((["'unsafe-inline'"] ) if DEBUG else []) + CSP_STYLE_SRC_EXTRA,
    'script-src': ["'self'"] + ((['http://127.0.0.1:5173', 'http://localhost:5173']) if DEBUG else []) + CSP_SCRIPT_SRC_EXTRA,
    'connect-src': ["'self'"] + ((['http://127.0.0.1:5173', 'http://localhost:5173']) if DEBUG else []) + CSP_CONNECT_SRC_EXTRA,
    'frame-src': ["'self'"] + CSP_FRAME_SRC_EXTRA,
    'form-action': ["'self'"],
}


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'users.authentication.RevokingJWTAuthentication',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '120/min',
        'user': '600/min',
        'auth_login': '5/min',
        'auth_register': '3/min',
        'auth_refresh': '10/min',
        'profile_update': '10/min',
        'email_change': '5/min',
    },

    'URL_FORMAT_OVERRIDE': None,
}

import sys
from importlib.util import find_spec
if any('test' in a for a in sys.argv):

    REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = ()
    REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].update({
        'anon': '1000000/min',
        'user': '1000000/min',
        'auth_login': '10000/min',
        'auth_register': '10000/min',
        'auth_refresh': '10000/min',
    })


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}

CLAMAV_HOST = config('CLAMAV_HOST', default='')
CLAMAV_PORT = config('CLAMAV_PORT', default=3310, cast=int)
AVATAR_SCAN_REQUIRED = config('AVATAR_SCAN_REQUIRED', default=False, cast=bool)
SECURITY_EMAIL_ALERTS_ENABLED = config('SECURITY_EMAIL_ALERTS_ENABLED', default=True, cast=bool)
LOGIN_LOCK_THRESHOLD = config('LOGIN_LOCK_THRESHOLD', default=5, cast=int)
LOGIN_LOCK_DURATION_SECONDS = config('LOGIN_LOCK_DURATION_SECONDS', default=900, cast=int)
ACTIVE_SESSION_INACTIVITY_TIMEOUT_SECONDS = config(
    'ACTIVE_SESSION_INACTIVITY_TIMEOUT_SECONDS',
    default=43200,
    cast=int,
)


CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173,http://localhost:3000',
    cast=Csv(),
)

CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=True, cast=bool)


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=10, cast=int)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER or 'webmaster@localhost')

REDIS_URL = config('REDIS_URL', default='redis://127.0.0.1:6379/1')
HAS_DJANGO_REDIS = find_spec('django_redis') is not None

USE_REDIS_CACHE = config('USE_REDIS_CACHE', default=False, cast=bool)

if (USE_REDIS_CACHE or (str(REDIS_URL).strip() and not DEBUG)) and HAS_DJANGO_REDIS:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'IGNORE_EXCEPTIONS': True,
            },
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'licenta-cache',
        }
    }


PASSWORD_MIN_LENGTH = config('PASSWORD_MIN_LENGTH', default=8, cast=int)
PASSWORD_MIN_ZXCVBN_SCORE = config('PASSWORD_MIN_ZXCVBN_SCORE', default=2, cast=int)
PASSWORD_BLACKLIST = config('PASSWORD_BLACKLIST', default='', cast=Csv())
CHECK_PWNED_PASSWORDS = config('CHECK_PWNED_PASSWORDS', default=False, cast=bool)

AWS_S3_BUCKET_NAME = config('AWS_S3_BUCKET_NAME', default='')
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
AWS_REGION = config('AWS_REGION', default='')
AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL', default='')
S3_PRESIGN_EXPIRY = config('S3_PRESIGN_EXPIRY', default=3600, cast=int)

CELERY_BROKER_URL = config('CELERY_BROKER_URL', default=REDIS_URL)
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

try:
    from celery.schedules import crontab

    CELERY_BEAT_SCHEDULE = {
        'evaluate-weekly-challenges': {
            'task': 'evaluate_weekly_challenges',
            'schedule': crontab(hour=0, minute=0, day_of_week=1),  
            'options': {'queue': 'default'},
        },
        'reset-weekly-challenges': {
            'task': 'reset_weekly_challenges',
            'schedule': crontab(hour=0, minute=5, day_of_week=1),  
            'options': {'queue': 'default'},
        },
        'precompute-recommendations-nightly': {
            'task': 'precompute_recommendations',
            'schedule': crontab(hour=2, minute=0),
            'options': {'queue': 'default'},
        },
        'precompute-compatibility-nightly': {
            'task': 'precompute_compatibility',
            'schedule': crontab(hour=3, minute=0),
            'options': {'queue': 'default'},
        },
    }
except ImportError:
    CELERY_BEAT_SCHEDULE = {}

try:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    SENTRY_DSN = config('SENTRY_DSN', default='')
    if SENTRY_DSN:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,        
            event_level=logging.ERROR,  
        )
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration(), sentry_logging],
            traces_sample_rate=float(config('SENTRY_TRACES_SAMPLE_RATE', default=0.0)),
            send_default_pii=config('SENTRY_SEND_PII', default=False, cast=bool),
        )
except Exception:
    pass

