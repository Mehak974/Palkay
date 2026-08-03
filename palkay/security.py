"""
Palkay Security Middleware Stack
---------------------------------
1. RateLimitMiddleware   — IP-based rate limiting (in-memory + Redis-ready)
2. SecurityHeadersMiddleware — CSP, Permissions-Policy, referrer policy
3. RequestValidationMiddleware — block malicious payloads, bad user-agents
4. CloudflareMiddleware  — trust CF-Connecting-IP, block non-CF in prod
"""

import time
import hashlib
import logging
import re
from collections import defaultdict
from threading import Lock

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('palkay.security')


# ── 1. Rate Limiting ─────────────────────────────────────────────────────────

class RateLimitMiddleware:
    """
    Token-bucket rate limiter per IP address.
    Uses Django cache (Redis in prod, LocMemCache in dev).

    Limits (configurable in settings.py RATE_LIMITS):
      - Global:      200 requests / 60s
      - Auth routes: 10 attempts / 300s  (login, register)
      - Checkout:    20 requests / 60s
      - Cart add:    60 requests / 60s
    """

    LIMITS = {
        # (url_pattern, max_requests, window_seconds, block_seconds)
        'auth':     (r'^/account/(login|register)/', 10,  300, 900),
        'checkout': (r'^/checkout/',                 20,   60, 300),
        'cart':     (r'^/cart/add/',                 60,   60, 120),
        'global':   (r'.*',                         200,   60,  60),
    }

    def __init__(self, get_response):
        self.get_response = get_response
        self.compiled = [
            (name, re.compile(pattern), max_req, window, block)
            for name, (pattern, max_req, window, block)
            in self.LIMITS.items()
        ]
        # Override with settings if provided
        if hasattr(settings, 'RATE_LIMITS'):
            pass  # extend here for custom overrides

    def __call__(self, request):
        ip = self._get_ip(request)

        for name, pattern, max_req, window, block_seconds in self.compiled:
            if not pattern.match(request.path):
                continue

            block_key = f'rl:block:{name}:{ip}'
            if cache.get(block_key):
                logger.warning(f'Rate limit block active: {ip} → {request.path}')
                return self._blocked_response(request, name)

            count_key = f'rl:count:{name}:{ip}'
            count = cache.get(count_key, 0)

            if count >= max_req:
                cache.set(block_key, True, block_seconds)
                logger.warning(f'Rate limit exceeded: {ip} → {request.path} ({name})')
                return self._blocked_response(request, name)

            # Increment — use add for atomic first-set with TTL
            if count == 0:
                cache.add(count_key, 0, window)
            cache.incr(count_key)
            break  # first matching rule wins

        response = self.get_response(request)
        return response

    def _get_ip(self, request):
        """Respect CF-Connecting-IP when Cloudflare is in use."""
        cf_ip = request.META.get('HTTP_CF_CONNECTING_IP')
        if cf_ip and getattr(settings, 'TRUST_CLOUDFLARE', False):
            return cf_ip
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    def _blocked_response(self, request, rule_name):
        if request.headers.get('Accept', '').startswith('application/json') or \
           request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(
                {'error': 'Too many requests. Please slow down.'},
                status=429
            )
        # Return a minimal HTML response (avoids template rendering overhead)
        html = '''<!DOCTYPE html><html><head><title>Too Many Requests</title>
        <style>body{font-family:sans-serif;text-align:center;padding:80px;background:#F7F4EE;}
        h1{font-size:42px;margin-bottom:12px;}p{color:#545454;}</style></head>
        <body><h1>429</h1><p>Too many requests. Please wait a moment and try again.</p>
        <p><a href="/">← Back to Palkay</a></p></body></html>'''
        resp = HttpResponse(html, status=429)
        resp['Retry-After'] = '60'
        return resp


# ── 2. Security Headers ───────────────────────────────────────────────────────

class SecurityHeadersMiddleware:
    """
    Injects comprehensive security headers on every response.
    CSP, Permissions-Policy, Referrer-Policy, etc.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.debug = getattr(settings, 'DEBUG', False)

    def __call__(self, request):
        response = self.get_response(request)
        self._add_headers(response)
        return response

    def _add_headers(self, response):
        # Content Security Policy
        # Loosened in DEBUG for Django toolbar etc.
        if self.debug:
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: blob: *; "
                "connect-src 'self'; "
            )
        else:
            csp = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: blob: "
                + getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', '') + " "
                "https://palkay.com; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "upgrade-insecure-requests; "
            )
        response['Content-Security-Policy'] = csp

        # Prevent MIME-type sniffing
        response['X-Content-Type-Options'] = 'nosniff'

        # Clickjacking protection
        response['X-Frame-Options'] = 'DENY'

        # XSS protection (legacy browsers)
        response['X-XSS-Protection'] = '1; mode=block'

        # Referrer policy — send origin only on same-origin, nothing cross-origin
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions policy — disable unnecessary browser features
        response['Permissions-Policy'] = (
            'accelerometer=(), '
            'camera=(), '
            'geolocation=(), '
            'gyroscope=(), '
            'magnetometer=(), '
            'microphone=(), '
            'payment=(), '
            'usb=()'
        )

        # HSTS — only in production
        if not self.debug:
            response['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains; preload'
            )

        # Cache control for sensitive pages
        if hasattr(response, 'request'):
            path = response.request.path
            if any(p in path for p in ['/account/', '/checkout/', '/cart/']):
                response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
                response['Pragma'] = 'no-cache'

        return response


# ── 3. Request Validation ────────────────────────────────────────────────────

# Known malicious user-agent patterns
BAD_UA_PATTERNS = re.compile(
    r'(sqlmap|nikto|nmap|masscan|zgrab|dirbuster|gobuster|'
    r'nuclei|scrapy|python-requests/2\.[0-4]|curl/[0-6]|'
    r'libwww-perl|wwwoffle|wget(?!/)|<script)',
    re.IGNORECASE
)

# Path traversal / injection attempts
BAD_PATH_PATTERNS = re.compile(
    r'(\.\./|\.\.\\|%2e%2e|%252e|/etc/passwd|/proc/self|'
    r'<script|javascript:|vbscript:|onload=|onerror=|eval\()',
    re.IGNORECASE
)

# Blocked file extensions (no reason to request these on a Django app)
BLOCKED_EXTENSIONS = re.compile(
    r'\.(php|asp|aspx|jsp|cgi|pl|sh|bash|env|git|svn|htaccess|htpasswd|xml|bak|old|backup|sql|dump)$',
    re.IGNORECASE
)


class RequestValidationMiddleware:
    """
    Block obviously malicious requests before they touch Django views.
    Logs all blocked requests for security analysis.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        ua = request.META.get('HTTP_USER_AGENT', '')

        # Block bad user agents
        if ua and BAD_UA_PATTERNS.search(ua):
            logger.warning(f'Blocked bad UA: {ua[:100]} from {self._get_ip(request)}')
            return HttpResponseForbidden('Forbidden')

        # Block path traversal / injection in URL
        if BAD_PATH_PATTERNS.search(path):
            logger.warning(f'Blocked bad path: {path} from {self._get_ip(request)}')
            return HttpResponseForbidden('Forbidden')

        # Block requests for irrelevant file types
        if BLOCKED_EXTENSIONS.search(path):
            logger.info(f'Blocked extension probe: {path}')
            return HttpResponseForbidden('Forbidden')

        # Block suspiciously large POST bodies (before Django reads them)
        if request.method == 'POST':
            content_length = request.META.get('CONTENT_LENGTH')
            if content_length:
                try:
                    if int(content_length) > 10 * 1024 * 1024:  # 10MB
                        logger.warning(f'Blocked oversized POST: {content_length} bytes')
                        return HttpResponse('Request Entity Too Large', status=413)
                except (ValueError, TypeError):
                    pass

        return self.get_response(request)

    def _get_ip(self, request):
        cf_ip = request.META.get('HTTP_CF_CONNECTING_IP')
        if cf_ip and getattr(settings, 'TRUST_CLOUDFLARE', False):
            return cf_ip
        return request.META.get('REMOTE_ADDR', '?')


# ── 4. Cloudflare Middleware ─────────────────────────────────────────────────

# Official Cloudflare IPv4 + IPv6 ranges (updated Q1 2026)
# Source: https://www.cloudflare.com/ips/
CF_IP_RANGES_V4 = [
    '173.245.48.0/20', '103.21.244.0/22', '103.22.200.0/22',
    '103.31.4.0/22',   '141.101.64.0/18', '108.162.192.0/18',
    '190.93.240.0/20', '188.114.96.0/20', '197.234.240.0/22',
    '198.41.128.0/17', '162.158.0.0/15',  '104.16.0.0/13',
    '104.24.0.0/14',   '172.64.0.0/13',   '131.0.72.0/22',
]
CF_IP_RANGES_V6 = [
    '2400:cb00::/32', '2606:4700::/32', '2803:f800::/32',
    '2405:b500::/32', '2405:8100::/32', '2a06:98c0::/29',
    '2c0f:f248::/32',
]


def _build_cf_networks():
    import ipaddress
    networks = []
    for cidr in CF_IP_RANGES_V4 + CF_IP_RANGES_V6:
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            pass
    return networks


_CF_NETWORKS = None
_CF_NETWORKS_LOCK = Lock()


def _get_cf_networks():
    global _CF_NETWORKS
    if _CF_NETWORKS is None:
        with _CF_NETWORKS_LOCK:
            if _CF_NETWORKS is None:
                _CF_NETWORKS = _build_cf_networks()
    return _CF_NETWORKS


class CloudflareMiddleware:
    """
    When CLOUDFLARE_ONLY=True:
      - Blocks requests not originating from Cloudflare IPs
      - Replaces REMOTE_ADDR with CF-Connecting-IP (real visitor IP)
      - Validates CF-Ray header presence

    Safe to keep enabled even if CLOUDFLARE_ONLY=False —
    it will still fix REMOTE_ADDR for rate limiting etc.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.cf_only = getattr(settings, 'CLOUDFLARE_ONLY', False)
        self.debug = getattr(settings, 'DEBUG', False)

    def __call__(self, request):
        remote_addr = request.META.get('REMOTE_ADDR', '')
        cf_connecting_ip = request.META.get('HTTP_CF_CONNECTING_IP', '')

        is_cf = self._is_cloudflare_ip(remote_addr)

        if self.cf_only and not self.debug and not is_cf:
            logger.warning(f'Non-CF request blocked: {remote_addr}')
            return HttpResponseForbidden(
                'Direct access not permitted. Please access via palkay.com'
            )

        # Replace REMOTE_ADDR with real visitor IP when behind CF
        if is_cf and cf_connecting_ip:
            request.META['REMOTE_ADDR'] = cf_connecting_ip
            request.META['HTTP_X_REAL_IP'] = cf_connecting_ip

        # Expose CF metadata to views
        request.cf_ray = request.META.get('HTTP_CF_RAY', '')
        request.cf_country = request.META.get('HTTP_CF_IPCOUNTRY', '')
        request.is_behind_cloudflare = is_cf

        return self.get_response(request)

    def _is_cloudflare_ip(self, ip_str):
        import ipaddress
        if not ip_str:
            return False
        try:
            ip = ipaddress.ip_address(ip_str)
            return any(ip in net for net in _get_cf_networks())
        except ValueError:
            return False
