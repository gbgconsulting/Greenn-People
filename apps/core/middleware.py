"""Middleware de hardening (headers de segurança em produção)."""


class SecurityHeadersMiddleware:
    """CSP e Referrer-Policy — complementa ``SecurityMiddleware`` do Django."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # HTMX via CDN; estilos inline mínimos em base.html (htmx-indicator).
        response.headers.setdefault(
            'Content-Security-Policy',
            (
                "default-src 'self'; "
                "script-src 'self' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),
        )
        response.headers.setdefault(
            'Referrer-Policy',
            'strict-origin-when-cross-origin',
        )
        return response
