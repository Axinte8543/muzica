"""Deterministic local tests; never use these settings to serve production."""
from .settings import *  # noqa: F403

DEBUG = True
SECURE_SSL_REDIRECT = False
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
SECRET_KEY = 'local-test-key-with-at-least-thirty-two-characters'
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
