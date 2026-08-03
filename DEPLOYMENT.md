# Palkay — Production Deployment Checklist

Run through every item before going live. Check off each one.

---

## 1. Server Setup

- [ ] Ubuntu 22.04+ / Debian 12 server provisioned
- [ ] Non-root deploy user created (`adduser deploy`)
- [ ] SSH key-only login (`PasswordAuthentication no` in sshd_config)
- [ ] UFW firewall: allow only 22 (SSH), 80 (HTTP), 443 (HTTPS)
  ```bash
  ufw allow ssh
  ufw allow 'Nginx Full'
  ufw enable
  ```
- [ ] `fail2ban` installed and enabled (protects SSH)
- [ ] Unattended security upgrades enabled

---

## 2. Dependencies

```bash
# Python
sudo apt install python3.11 python3.11-venv python3-pip

# PostgreSQL
sudo apt install postgresql postgresql-contrib

# Redis
sudo apt install redis-server
sudo systemctl enable redis-server

# Nginx
sudo apt install nginx

# Certbot (Let's Encrypt SSL for origin cert)
sudo apt install certbot python3-certbot-nginx
```

---

## 3. PostgreSQL Setup

```sql
-- As postgres user:
CREATE USER palkay_user WITH PASSWORD 'strongrandompassword';
CREATE DATABASE palkay_db OWNER palkay_user;
GRANT ALL PRIVILEGES ON DATABASE palkay_db TO palkay_user;
```

---

## 4. Application Deployment

```bash
# Clone
git clone https://github.com/yourorg/palkay.git /var/www/palkay
cd /var/www/palkay

# Virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Environment
cp .env.example .env
# Edit .env with production values

# Collect static files
python manage.py collectstatic --noinput

# Database
python manage.py migrate
python manage.py seed_data
python manage.py createsuperuser

# Logs directory
mkdir -p logs
```

---

## 5. Gunicorn Service

```ini
# /etc/systemd/system/palkay.service
[Unit]
Description=Palkay Gunicorn Application Server
After=network.target

[Service]
User=deploy
Group=www-data
WorkingDirectory=/var/www/palkay
Environment="DJANGO_SETTINGS_MODULE=palkay.settings_production"
EnvironmentFile=/var/www/palkay/.env
ExecStart=/var/www/palkay/venv/bin/gunicorn \
    --workers 3 \
    --worker-class sync \
    --bind unix:/run/palkay.sock \
    --timeout 30 \
    --keep-alive 5 \
    --log-level warning \
    --error-logfile /var/www/palkay/logs/gunicorn-error.log \
    --access-logfile /var/www/palkay/logs/gunicorn-access.log \
    palkay.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable palkay
sudo systemctl start palkay
sudo systemctl status palkay
```

**Workers formula:** `(2 × CPU cores) + 1` — e.g. 2 cores → 5 workers.

---

## 6. Nginx Configuration

```nginx
# /etc/nginx/sites-available/palkay
server {
    listen 80;
    server_name palkay.com www.palkay.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name palkay.com www.palkay.com;

    # SSL (managed by Certbot)
    ssl_certificate     /etc/letsencrypt/live/palkay.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/palkay.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 1d;

    # Restrict to Cloudflare IPs only (highly recommended)
    # Paste current list from https://www.cloudflare.com/ips/
    # Allow Cloudflare IPv4:
    allow 173.245.48.0/20;
    allow 103.21.244.0/22;
    allow 103.22.200.0/22;
    allow 103.31.4.0/22;
    allow 141.101.64.0/18;
    allow 108.162.192.0/18;
    allow 190.93.240.0/20;
    allow 188.114.96.0/20;
    allow 197.234.240.0/22;
    allow 198.41.128.0/17;
    allow 162.158.0.0/15;
    allow 104.16.0.0/13;
    allow 104.24.0.0/14;
    allow 172.64.0.0/13;
    allow 131.0.72.0/22;
    # Allow localhost (for health checks)
    allow 127.0.0.1;
    deny all;

    # Pass real visitor IP from Cloudflare
    set_real_ip_from 173.245.48.0/20;
    set_real_ip_from 103.21.244.0/22;
    real_ip_header CF-Connecting-IP;

    # Client body size
    client_max_body_size 10M;

    # Static files — served by WhiteNoise via Django, but Nginx handles /media/
    location /media/ {
        alias /var/www/palkay/media/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Proxy to Gunicorn
    location / {
        proxy_pass         http://unix:/run/palkay.sock;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_redirect     off;
        proxy_read_timeout 30s;
        proxy_connect_timeout 10s;
    }
}
```

```bash
sudo nginx -t
sudo ln -s /etc/nginx/sites-available/palkay /etc/nginx/sites-enabled/
sudo systemctl reload nginx

# SSL certificate
sudo certbot --nginx -d palkay.com -d www.palkay.com
```

---

## 7. Django Settings Checklist

- [ ] `DEBUG=False`
- [ ] `SECRET_KEY` is long (50+ chars), random, not in version control
- [ ] `ALLOWED_HOSTS` contains only your domain
- [ ] `ADMIN_URL` changed from `admin/` to random slug
- [ ] `CLOUDFLARE_ONLY=True` (after Cloudflare fully set up)
- [ ] `TRUST_CLOUDFLARE=True`
- [ ] Database is PostgreSQL (not SQLite)
- [ ] Redis is configured for cache + sessions
- [ ] `USE_S3=True` for media files (or configure Nginx /media/ serving)
- [ ] Email is configured (SMTP, not console backend)

---

## 8. Cloudflare Checklist

- [ ] Domain added to Cloudflare, nameservers updated
- [ ] DNS records added (A records proxied / orange cloud)
- [ ] SSL mode: **Full (Strict)**
- [ ] Always Use HTTPS: **ON**
- [ ] HSTS enabled (max-age 1 year, include subdomains, preload)
- [ ] Minimum TLS: **1.2**
- [ ] Bot Fight Mode: **ON**
- [ ] Browser Integrity Check: **ON**
- [ ] WAF Custom Rules added (see cloudflare_setup.py)
- [ ] Cache Rules added (bypass account/checkout, cache static/products)
- [ ] Rate Limiting rules added (login brute force, global flood)
- [ ] Auto Minify: HTML + CSS + JS
- [ ] Brotli: **ON**
- [ ] HTTP/2 + HTTP/3: **ON**
- [ ] Early Hints: **ON**

---

## 9. Security Verification

```bash
# Test security headers
curl -I https://palkay.com | grep -E "(Strict|X-Frame|Content-Security|X-Content)"

# Test rate limiting
for i in $(seq 1 15); do curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST https://palkay.com/account/login/; done

# Test admin URL is non-default
curl -s -o /dev/null -w "%{http_code}" https://palkay.com/admin/
# Should return 404, not 200

# Check SSL rating
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=palkay.com
# Target: A or A+

# Check security headers grade
# Visit: https://securityheaders.com/?q=palkay.com
# Target: A or A+
```

---

## 10. Performance Verification

```bash
# Check static files are compressed
curl -H "Accept-Encoding: br" -I https://palkay.com/static/css/palkay.css \
  | grep -i "content-encoding"
# Should show: content-encoding: br

# Check Cloudflare cache is working
curl -I https://palkay.com/ | grep -i "cf-cache-status"
# Should show: CF-Cache-Status: HIT (after first request)

# Check homepage load time
curl -o /dev/null -s -w "Total: %{time_total}s\n" https://palkay.com/
# Target: <200ms on repeat requests (cached)
```

---

## 11. Ongoing Operations

```bash
# Deploy update
cd /var/www/palkay
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart palkay

# View logs
sudo journalctl -u palkay -f           # Gunicorn logs
tail -f logs/security.log              # Security events
tail -f logs/gunicorn-error.log        # Application errors

# Clear Django cache (e.g. after bulk product update)
python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Cloudflare cache purge (via dashboard or API)
# Dashboard: Caching → Configuration → Purge Everything
```

---

## Worker Count Reference

| Server vCPUs | Gunicorn Workers | Notes |
|---|---|---|
| 1 | 3 | Minimum viable |
| 2 | 5 | Good for 100–500 rps |
| 4 | 9 | Recommended for growth |
| 8 | 17 | High traffic |

For CPU-bound tasks, reduce workers and add threads:
`--workers 3 --threads 2`
