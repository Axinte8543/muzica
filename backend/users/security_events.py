import json
import logging
import os

try:
	import sentry_sdk
except Exception:
	sentry_sdk = None


def emit_security_signal(event_name: str, *, severity: str = 'info', **payload) -> None:
\
\
\
\
\
\
    
	event_name = str(event_name or '').strip()
	if not event_name:
		return
	message = {
	 'event_name': event_name,
	 'severity': severity,
	 **payload,
	}

	if sentry_sdk:
		try:
			with sentry_sdk.push_scope() as scope:
				scope.set_tag('security_event', event_name)
				scope.set_tag('security_severity', severity)
				for key, value in payload.items():
					scope.set_extra(key, value)
				sentry_sdk.capture_message(event_name, level=severity)
		except Exception:
			pass

	siem_stdout = str(os.environ.get('SECURITY_AUDIT_EXPORT_STDOUT', '') or '').strip().lower() in {'1', 'true', 'yes', 'on'}
	siem_url = str(os.environ.get('SECURITY_AUDIT_EXPORT_URL', '') or '').strip()
	if siem_stdout or siem_url:
		try:
			from urllib.request import Request, urlopen
			body = json.dumps(message, ensure_ascii=False).encode('utf-8')
			if siem_url:
				req = Request(siem_url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
				with urlopen(req, timeout=3):
					pass
			else:
				print(json.dumps(message, ensure_ascii=False), flush=True)
		except Exception:
			logging.exception('Failed to emit security signal %s', event_name)