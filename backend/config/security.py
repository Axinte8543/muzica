from django.conf import settings


class SecurityHeadersMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		response = self.get_response(request)
		self._apply_headers(response)
		return response

	def _apply_headers(self, response):
		response.setdefault('X-Content-Type-Options', 'nosniff')
		response.setdefault('Referrer-Policy', getattr(settings, 'SECURE_REFERRER_POLICY', 'strict-origin-when-cross-origin'))
		response.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=(), usb=()')
		response.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
		response.setdefault('Cross-Origin-Resource-Policy', 'same-site')
		csp = self._build_csp()
		if csp:
			response.setdefault('Content-Security-Policy', csp)

	def _build_csp(self):
		directives = getattr(settings, 'DEFAULT_CSP_DIRECTIVES', {}) or {}
		parts = []
		for directive, values in directives.items():
			if not values:
				parts.append(directive)
				continue
			parts.append(f"{directive} {' '.join(values)}")
		return '; '.join(parts)