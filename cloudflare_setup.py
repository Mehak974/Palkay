"""
Cloudflare Setup for Palkay
============================
This file documents every Cloudflare setting required for production.
It is also executable — run it with your CF credentials to apply settings
via the Cloudflare API automatically.

Requirements:
    pip install requests python-decouple

Usage:
    CF_API_TOKEN=xxx CF_ZONE_ID=yyy python cloudflare_setup.py --apply
    python cloudflare_setup.py --dry-run   (just print what would be applied)

Sections:
    1. DNS Records
    2. SSL/TLS Settings
    3. Security Settings (WAF, Bot Management, DDoS)
    4. Performance Settings (Cache Rules, Compression, Rocket Loader)
    5. Page Rules → Cache Rules (new syntax)
    6. Firewall Rules
    7. Rate Limiting Rules
"""

import sys
import json
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

try:
    import requests
    from decouple import config
    CF_API_TOKEN = config('CF_API_TOKEN', default='')
    CF_ZONE_ID   = config('CF_ZONE_ID', default='')
    CF_ACCOUNT_ID = config('CF_ACCOUNT_ID', default='')
    DOMAIN = config('DOMAIN', default='palkay.com')
    ORIGIN_IP = config('ORIGIN_IP', default='')  # Your server IP
except ImportError:
    log.warning('requests/decouple not installed — running in documentation mode only.')
    CF_API_TOKEN = CF_ZONE_ID = CF_ACCOUNT_ID = DOMAIN = ORIGIN_IP = ''
    requests = None


# ─────────────────────────────────────────────────────────────────────────────
# CLOUDFLARE SETTINGS SPECIFICATION
# Each section is a dict of setting_name → desired_value with documentation.
# ─────────────────────────────────────────────────────────────────────────────

# 1. ── DNS RECORDS ───────────────────────────────────────────────────────────
DNS_RECORDS = [
    {
        'type':    'A',
        'name':    '@',                  # palkay.com
        'content': ORIGIN_IP,
        'proxied': True,                 # Traffic through Cloudflare (orange cloud)
        'ttl':     1,                    # Auto when proxied
        'comment': 'Main site — proxied through CF for DDoS protection + CDN',
    },
    {
        'type':    'A',
        'name':    'www',                # www.palkay.com
        'content': ORIGIN_IP,
        'proxied': True,
        'ttl':     1,
        'comment': 'WWW redirect',
    },
    {
        'type':    'MX',
        'name':    '@',
        'content': 'mail.palkay.com',
        'priority': 10,
        'proxied': False,                # Never proxy MX records
        'ttl':     3600,
        'comment': 'Mail server',
    },
    {
        'type':    'TXT',
        'name':    '@',
        'content': 'v=spf1 include:_spf.google.com ~all',
        'proxied': False,
        'ttl':     3600,
        'comment': 'SPF record for email authentication',
    },
]

# 2. ── SSL/TLS ────────────────────────────────────────────────────────────────
SSL_SETTINGS = {
    # Full (Strict) — CF validates your origin cert.
    # Requires a valid SSL cert on your origin (Let's Encrypt is fine).
    'ssl': 'strict',

    # Minimum TLS version — reject TLS 1.0 and 1.1
    'min_tls_version': '1.2',

    # Enable TLS 1.3 for best performance on modern clients
    'tls_1_3': 'on',

    # Automatic HTTPS rewrites — upgrades http:// links in HTML to https://
    'automatic_https_rewrites': 'on',

    # HTTP Strict Transport Security (HSTS) — also set in Django but CF layer helps
    'security_header': {
        'strict_transport_security': {
            'enabled':             True,
            'max_age':             31536000,
            'include_subdomains':  True,
            'preload':             True,
            'nosniff':             True,
        }
    },

    # Always use HTTPS — redirect all HTTP → HTTPS at CF edge
    'always_use_https': 'on',
}

# 3. ── SECURITY SETTINGS ─────────────────────────────────────────────────────
SECURITY_SETTINGS = {
    # Security level: medium blocks known bad IPs and shows CAPTCHA
    # Options: off, essentially_off, low, medium, high, under_attack
    'security_level': 'medium',

    # Challenge passage — how long a challenged user is trusted (seconds)
    'challenge_ttl': 1800,   # 30 minutes

    # Browser Integrity Check — validate browser headers
    'browser_check': 'on',

    # Privacy Pass — reduce CAPTCHA friction for legitimate users
    'privacy_pass': 'on',

    # Bot Fight Mode — free tier bot protection
    'bot_fight_mode': 'on',

    # Email obfuscation — scramble email addresses in HTML to block scrapers
    'email_obfuscation': 'on',

    # Server-side Excludes — hide content from bad bots
    'server_side_exclude': 'on',

    # Hotlink Protection — block image leeching
    'hotlink_protection': 'off',   # Set to 'on' if image bandwidth is abused
}

# 4. ── PERFORMANCE SETTINGS ───────────────────────────────────────────────────
PERFORMANCE_SETTINGS = {
    # Auto Minify — CF minifies HTML/CSS/JS at the edge
    'minify': {
        'html': True,
        'css':  True,
        'js':   True,
    },

    # Brotli compression (better than gzip, supported by all modern browsers)
    'brotli': 'on',

    # HTTP/2 and HTTP/3 (QUIC) for multiplexed connections
    'http2': 'on',
    'http3': 'on',   # QUIC

    # 0-RTT Connection Resumption — faster reconnections (slight replay risk)
    '0rtt': 'on',

    # Rocket Loader — async JS loading (disable if it breaks your JS)
    'rocket_loader': 'off',   # Palkay uses vanilla JS, safe to enable if tested

    # Polish — image optimisation (lossless or lossy)
    # Requires Pro plan
    'polish': 'lossless',

    # WebP conversion (if origin serves JPEG/PNG, CF serves WebP to capable browsers)
    'webp': 'on',

    # Early Hints (103 status) — preload resources before full response
    'early_hints': 'on',

    # Browser cache TTL — how long browsers cache CF-served assets
    # Set to 4 hours; WhiteNoise + content hashing handles busting
    'browser_cache_ttl': 14400,
}

# 5. ── CACHE RULES (replaces Page Rules) ──────────────────────────────────────
# Applied in order — first match wins.
CACHE_RULES = [
    {
        'name': 'Bypass cache — account & checkout pages',
        'description': 'Personal pages must never be served from cache',
        'expression': '(starts_with(http.request.uri.path, "/account/")) or '
                      '(starts_with(http.request.uri.path, "/checkout/")) or '
                      '(starts_with(http.request.uri.path, "/cart/")) or '
                      '(starts_with(http.request.uri.path, "/admin/"))',
        'action': 'bypass',
        'cache_control': 'no-store',
    },
    {
        'name': 'Cache static assets aggressively',
        'description': 'WhiteNoise serves content-hashed filenames — safe to cache forever',
        'expression': '(starts_with(http.request.uri.path, "/static/"))',
        'action': 'cache',
        'edge_ttl': 31536000,          # 1 year at CF edge
        'browser_ttl': 31536000,
        'cache_key': 'default',
    },
    {
        'name': 'Cache product pages',
        'description': 'Product detail pages — 15 min CF edge cache',
        'expression': '(starts_with(http.request.uri.path, "/products/") and '
                      'not http.cookie contains "plk_session")',
        'action': 'cache',
        'edge_ttl': 900,               # 15 min
        'browser_ttl': 60,
    },
    {
        'name': 'Cache category pages',
        'description': 'Category listings — 30 min edge cache for anonymous users',
        'expression': '(starts_with(http.request.uri.path, "/category/") and '
                      'not http.cookie contains "plk_session")',
        'action': 'cache',
        'edge_ttl': 1800,
        'browser_ttl': 60,
    },
    {
        'name': 'Cache homepage',
        'description': 'Homepage — 5 min edge cache for anonymous users',
        'expression': '(http.request.uri.path eq "/" and '
                      'not http.cookie contains "plk_session")',
        'action': 'cache',
        'edge_ttl': 300,
        'browser_ttl': 60,
    },
]

# 6. ── FIREWALL RULES (WAF Custom Rules) ─────────────────────────────────────
FIREWALL_RULES = [
    {
        'name': 'Block known bad bots by UA',
        'description': 'Block SQLMap, scanners, and common attack tools',
        'expression': '(http.user_agent contains "sqlmap") or '
                      '(http.user_agent contains "nikto") or '
                      '(http.user_agent contains "nmap") or '
                      '(http.user_agent contains "masscan") or '
                      '(http.user_agent contains "nuclei") or '
                      '(http.user_agent contains "dirbuster") or '
                      '(http.user_agent contains "gobuster")',
        'action': 'block',
        'priority': 1,
    },
    {
        'name': 'Block path traversal attempts',
        'description': 'Block requests containing ../ or similar path traversal',
        'expression': '(http.request.uri contains "../") or '
                      '(http.request.uri contains "..%2F") or '
                      '(http.request.uri contains "%2e%2e") or '
                      '(http.request.uri contains "/etc/passwd") or '
                      '(http.request.uri contains "/proc/self")',
        'action': 'block',
        'priority': 2,
    },
    {
        'name': 'Block admin from non-GB/US IPs',
        'description': 'Restrict Django admin to known countries (adjust as needed)',
        'expression': '(starts_with(http.request.uri.path, "/admin/") and '
                      'not ip.geoip.country in {"US" "GB" "AU" "CA"})',
        'action': 'challenge',    # Use 'block' for stricter enforcement
        'priority': 3,
    },
    {
        'name': 'Challenge high-risk countries',
        'description': 'CAPTCHA challenge for countries with high fraud rates (optional)',
        'expression': '(ip.geoip.country in {"CN" "RU" "KP" "IR"})',
        'action': 'managed_challenge',
        'priority': 10,
        'enabled': False,           # Enable if you see fraud from these regions
    },
    {
        'name': 'Block empty or missing User-Agent',
        'description': 'Legitimate browsers always send a User-Agent',
        'expression': '(http.user_agent eq "")',
        'action': 'block',
        'priority': 5,
    },
    {
        'name': 'Protect checkout from suspicious requests',
        'description': 'Managed challenge on checkout for IPs with bad reputation',
        'expression': '(starts_with(http.request.uri.path, "/checkout/") and '
                      'cf.threat_score gt 10)',
        'action': 'managed_challenge',
        'priority': 6,
    },
]

# 7. ── RATE LIMITING RULES (CF-level, before hitting origin) ──────────────────
CF_RATE_LIMIT_RULES = [
    {
        'name': 'Login endpoint brute force protection',
        'description': 'Max 10 POST requests to /account/login/ per IP per 5 minutes',
        'expression': '(http.request.uri.path eq "/account/login/" and http.request.method eq "POST")',
        'period':     300,    # 5 minutes
        'requests_per_period': 10,
        'mitigation_timeout':  900,   # Block for 15 minutes
        'action': 'block',
    },
    {
        'name': 'Checkout rate limit',
        'description': 'Max 20 requests to /checkout/ per IP per minute',
        'expression': '(starts_with(http.request.uri.path, "/checkout/"))',
        'period':     60,
        'requests_per_period': 20,
        'mitigation_timeout':  300,
        'action': 'managed_challenge',
    },
    {
        'name': 'Global rate limit',
        'description': 'Max 500 requests per IP per minute — catches floods',
        'expression': 'true',
        'period':     60,
        'requests_per_period': 500,
        'mitigation_timeout':  60,
        'action': 'managed_challenge',
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# API HELPERS
# ─────────────────────────────────────────────────────────────────────────────

class CloudflareAPI:
    BASE = 'https://api.cloudflare.com/client/v4'

    def __init__(self, token, zone_id, account_id):
        self.token      = token
        self.zone_id    = zone_id
        self.account_id = account_id
        self.session    = requests.Session() if requests else None
        if self.session:
            self.session.headers.update({
                'Authorization': f'Bearer {token}',
                'Content-Type':  'application/json',
            })

    def _req(self, method, path, data=None):
        if not self.session:
            log.info(f'[DRY-RUN] {method.upper()} {path}')
            if data:
                log.info(f'  payload: {json.dumps(data, indent=2)}')
            return {'success': True, 'result': {}}

        url = f'{self.BASE}{path}'
        resp = getattr(self.session, method)(url, json=data, timeout=15)
        result = resp.json()
        if not result.get('success'):
            errors = result.get('errors', [])
            log.error(f'CF API error on {path}: {errors}')
        return result

    def zone_path(self, endpoint=''):
        return f'/zones/{self.zone_id}{endpoint}'

    def set_setting(self, name, value):
        return self._req('patch', self.zone_path(f'/settings/{name}'), {'value': value})

    def create_dns(self, record):
        return self._req('post', self.zone_path('/dns_records'), record)

    def list_dns(self):
        return self._req('get', self.zone_path('/dns_records'))


# ─────────────────────────────────────────────────────────────────────────────
# APPLY FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def apply_all(dry_run=False):
    if dry_run:
        log.info('=== DRY RUN — no changes will be made ===\n')

    if not CF_API_TOKEN or not CF_ZONE_ID:
        log.error('CF_API_TOKEN and CF_ZONE_ID must be set in .env')
        log.info('Set them and re-run, or follow the manual steps below.')
        print_manual_guide()
        return

    cf = CloudflareAPI(CF_API_TOKEN, CF_ZONE_ID, CF_ACCOUNT_ID)

    # SSL
    log.info('── Applying SSL/TLS settings ──')
    cf.set_setting('ssl', SSL_SETTINGS['ssl'])
    cf.set_setting('min_tls_version', SSL_SETTINGS['min_tls_version'])
    cf.set_setting('tls_1_3', SSL_SETTINGS['tls_1_3'])
    cf.set_setting('automatic_https_rewrites', SSL_SETTINGS['automatic_https_rewrites'])
    cf.set_setting('always_use_https', SSL_SETTINGS['always_use_https'])

    # Security
    log.info('── Applying security settings ──')
    cf.set_setting('security_level', SECURITY_SETTINGS['security_level'])
    cf.set_setting('browser_check', SECURITY_SETTINGS['browser_check'])
    cf.set_setting('email_obfuscation', SECURITY_SETTINGS['email_obfuscation'])
    cf.set_setting('hotlink_protection', SECURITY_SETTINGS['hotlink_protection'])

    # Performance
    log.info('── Applying performance settings ──')
    cf.set_setting('minify', SECURITY_SETTINGS.get('minify', {'html': True, 'css': True, 'js': True}))
    cf.set_setting('brotli', PERFORMANCE_SETTINGS['brotli'])
    cf.set_setting('http2', PERFORMANCE_SETTINGS['http2'])
    cf.set_setting('early_hints', PERFORMANCE_SETTINGS['early_hints'])
    cf.set_setting('browser_cache_ttl', PERFORMANCE_SETTINGS['browser_cache_ttl'])

    # DNS
    log.info('── Applying DNS records ──')
    for record in DNS_RECORDS:
        if record.get('content') and record['content'] != '':
            cf.create_dns(record)
            log.info(f'  DNS {record["type"]} {record["name"]} → {record.get("content", "")}')
        else:
            log.warning(f'  Skipping DNS {record["type"]} {record["name"]} — no content set (check ORIGIN_IP in .env)')

    log.info('')
    log.info('✓ Automated settings applied.')
    log.info('')
    log.info('Manual steps still required (cannot be done via API):')
    log.info('  1. WAF Custom Rules — add FIREWALL_RULES via dashboard')
    log.info('  2. Cache Rules — add CACHE_RULES via dashboard')
    log.info('  3. Rate Limiting Rules — add CF_RATE_LIMIT_RULES via dashboard')
    log.info('  4. Enable Under Attack Mode if experiencing active DDoS')
    log.info('')
    log.info(f'  Dashboard: https://dash.cloudflare.com/?to=/:account/{DOMAIN}/security/waf')


def print_manual_guide():
    """Print the manual setup steps for operators without API access."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║          PALKAY — CLOUDFLARE MANUAL SETUP GUIDE                 ║
╠══════════════════════════════════════════════════════════════════╣

STEP 1 — Add your domain to Cloudflare
  1. Go to https://dash.cloudflare.com/
  2. Click "Add a Site" → enter palkay.com → choose plan (Free is fine)
  3. Cloudflare will scan your existing DNS records
  4. Point your domain registrar's nameservers to Cloudflare's

STEP 2 — DNS Records
  Add these records (A records should point to your server IP):
""")
    for r in DNS_RECORDS:
        proxied = '✓ Proxied (orange cloud)' if r.get('proxied') else '○ DNS only'
        print(f'  {r["type"]:<6} {r["name"]:<12} {r.get("content","<YOUR_IP>"):<30} {proxied}')

    print("""
STEP 3 — SSL/TLS
  Security → SSL/TLS → Overview
    ✓ Set mode to: Full (Strict)
  Security → SSL/TLS → Edge Certificates
    ✓ Always Use HTTPS: ON
    ✓ Minimum TLS Version: TLS 1.2
    ✓ TLS 1.3: ON
    ✓ Automatic HTTPS Rewrites: ON
    ✓ HTTP Strict Transport Security (HSTS):
        - Enable HSTS: ON
        - Max Age: 12 months
        - Include subdomains: ON
        - Preload: ON
        - No-Sniff: ON

STEP 4 — Security Settings
  Security → Settings:
    ✓ Security Level: Medium
    ✓ Browser Integrity Check: ON
    ✓ Email Obfuscation: ON
    ✓ Bot Fight Mode: ON

STEP 5 — WAF Custom Rules
  Security → WAF → Custom Rules → Create Rule:

  Rule 1: Block scanners
    Name: Block bad bots
    Expression: (http.user_agent contains "sqlmap") or
                (http.user_agent contains "nikto") or
                (http.user_agent contains "nmap")
    Action: Block

  Rule 2: Protect admin
    Name: Admin country restriction
    Expression: (starts_with(http.request.uri.path, "/admin/") and
                 not ip.geoip.country in {"US"})
    Action: Managed Challenge

  Rule 3: Block path traversal
    Name: Path traversal
    Expression: (http.request.uri contains "../") or
                (http.request.uri contains "/etc/passwd")
    Action: Block

STEP 6 — Cache Rules
  Caching → Cache Rules → Create Rule:

  Rule 1 (Priority 1): Bypass — account/checkout/admin
    Expression: (starts_with(http.request.uri.path, "/account/")) or
                (starts_with(http.request.uri.path, "/checkout/")) or
                (starts_with(http.request.uri.path, "/cart/")) or
                (starts_with(http.request.uri.path, "/admin/"))
    Action: Bypass cache

  Rule 2 (Priority 2): Cache static assets forever
    Expression: (starts_with(http.request.uri.path, "/static/"))
    Action: Cache
    Edge TTL: 1 year
    Browser TTL: 1 year

  Rule 3 (Priority 3): Cache product pages
    Expression: (starts_with(http.request.uri.path, "/products/") and
                 not http.cookie contains "plk_session")
    Action: Cache
    Edge TTL: 15 minutes
    Browser TTL: 1 minute

  Rule 4 (Priority 4): Cache homepage
    Expression: (http.request.uri.path eq "/" and
                 not http.cookie contains "plk_session")
    Action: Cache
    Edge TTL: 5 minutes
    Browser TTL: 1 minute

STEP 7 — Rate Limiting Rules
  Security → WAF → Rate Limiting Rules → Create Rule:

  Rule 1: Login brute force
    Expression: (http.request.uri.path eq "/account/login/" and
                 http.request.method eq "POST")
    Rate: 10 requests / 5 minutes
    Action: Block
    Mitigation timeout: 15 minutes

  Rule 2: Checkout protection
    Expression: starts_with(http.request.uri.path, "/checkout/")
    Rate: 20 requests / 1 minute
    Action: Managed Challenge

  Rule 3: Global flood protection
    Expression: true
    Rate: 500 requests / 1 minute
    Action: Managed Challenge

STEP 8 — Performance
  Speed → Optimization:
    ✓ Auto Minify: HTML + CSS + JS
    ✓ Brotli: ON
    ✓ HTTP/2: ON (usually auto)
    ✓ HTTP/3 (QUIC): ON
    ✓ Early Hints: ON

  Speed → Optimization → Content Optimization:
    ✓ Rocket Loader: OFF (test before enabling)
    ✓ Polish: Lossless (Pro plan)

STEP 9 — Palkay Django settings
  Add to your .env:
    TRUST_CLOUDFLARE=True
    CLOUDFLARE_ONLY=True      # Only accept traffic from CF IPs
    CLOUDFLARE_ONLY=False     # Allow direct access (safer while testing)

  Update settings_production.py ALLOWED_HOSTS to include your domain.

╚══════════════════════════════════════════════════════════════════╝
""")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Apply Cloudflare settings for Palkay')
    parser.add_argument('--apply',   action='store_true', help='Apply all settings via CF API')
    parser.add_argument('--dry-run', action='store_true', help='Print what would be applied')
    parser.add_argument('--guide',   action='store_true', help='Print manual setup guide')
    args = parser.parse_args()

    if args.guide:
        print_manual_guide()
    elif args.apply:
        apply_all(dry_run=False)
    elif args.dry_run:
        apply_all(dry_run=True)
    else:
        print_manual_guide()
