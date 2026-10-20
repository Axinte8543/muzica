from config.celery import app
import socket
import struct
from io import BytesIO
import boto3
from django.conf import settings
from django.utils import timezone
from .models import UserPrivacySettings, AvatarScanStatus
from .security_events import emit_security_signal


@app.task(bind=True, name='users.scan_avatar_object')
def scan_avatar_object(self, bucket: str, key: str, user_id: int):
                                                                                                            
    host = str(getattr(settings, 'CLAMAV_HOST', '') or '').strip()
    port = int(getattr(settings, 'CLAMAV_PORT', 3310) or 3310)
    profile = None
    try:
        profile = UserPrivacySettings.objects.get(user_id=user_id)
    except Exception:
        profile = None

    if not host:
                                             
        if getattr(settings, 'AVATAR_SCAN_REQUIRED', False) and profile is not None:
            profile.avatar_scan_status = AvatarScanStatus.FAILED
            profile.avatar_scan_message = 'malware scanner not configured'
            profile.avatar_scanned_at = timezone.now()
            profile.save(update_fields=['avatar_scan_status', 'avatar_scan_message', 'avatar_scanned_at'])
        return False, 'scanner not configured'

    try:
        s3 = boto3.client('s3',
                          aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                          aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
                          region_name=getattr(settings, 'AWS_REGION', None),
                          endpoint_url=getattr(settings, 'AWS_S3_ENDPOINT_URL', None) or None)
        obj = s3.get_object(Bucket=bucket, Key=key)
        data = obj['Body'].read()
    except Exception as e:
        if profile is not None:
            profile.avatar_scan_status = AvatarScanStatus.FAILED
            profile.avatar_scan_message = f's3 error: {e}'[:255]
            profile.avatar_scanned_at = timezone.now()
            profile.save(update_fields=['avatar_scan_status', 'avatar_scan_message', 'avatar_scanned_at'])
        return False, f's3 error: {e}'

    try:
        with socket.create_connection((host, port), timeout=15) as sock:
            sock.sendall(b'zINSTREAM\0')
            stream = BytesIO(data)
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    sock.sendall(struct.pack('!I', 0))
                    break
                sock.sendall(struct.pack('!I', len(chunk)))
                sock.sendall(chunk)
            resp = sock.recv(4096).decode('utf-8', errors='ignore')
        if 'FOUND' in resp.upper():
            msg = resp.strip()[:255]
            if profile is not None:
                profile.avatar_scan_status = AvatarScanStatus.REJECTED
                profile.avatar_scan_message = msg
                profile.avatar_scanned_at = timezone.now()
                profile.save(update_fields=['avatar_scan_status', 'avatar_scan_message', 'avatar_scanned_at'])
            emit_security_signal('avatar_rejected', severity='warning', user_id=user_id, bucket=bucket, key=key, message=msg)
            return False, msg
               
        if profile is not None:
            profile.avatar_scan_status = AvatarScanStatus.CLEAN
            profile.avatar_scan_message = resp.strip()[:255]
            profile.avatar_scanned_at = timezone.now()
            profile.save(update_fields=['avatar_scan_status', 'avatar_scan_message', 'avatar_scanned_at'])
        return True, resp.strip()
    except Exception as exc:
        if profile is not None:
            profile.avatar_scan_status = AvatarScanStatus.FAILED
            profile.avatar_scan_message = f'scan error: {exc}'[:255]
            profile.avatar_scanned_at = timezone.now()
            profile.save(update_fields=['avatar_scan_status', 'avatar_scan_message', 'avatar_scanned_at'])
        emit_security_signal('avatar_scan_failed', severity='error', user_id=user_id, bucket=bucket, key=key, error=str(exc)[:255])
        return False, f'scan error: {exc}'
