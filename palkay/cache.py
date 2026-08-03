"""
Palkay Cache Utilities
-----------------------
View-level caching helpers, cache key builders, and invalidation signals.
Import these in views to add caching with one decorator.
"""

import hashlib
import logging
from functools import wraps

from django.core.cache import cache
from django.utils.cache import patch_cache_control
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)

# ── TTLs (seconds) ───────────────────────────────────────────────────────────
TTL_HOME        = 60 * 5     #  5 min  — homepage (featured, new arrivals)
TTL_PRODUCT     = 60 * 15    # 15 min  — product detail page
TTL_CATEGORY    = 60 * 30    # 30 min  — category listing
TTL_BRAND       = 60 * 30    # 30 min  — brand listing
TTL_NAV         = 60 * 60    # 60 min  — nav categories (rarely changes)
TTL_CMS         = 60 * 60 * 4  # 4 hr — CMS pages


# ── Key builders ─────────────────────────────────────────────────────────────

def cache_key(*parts):
    """Build a namespaced cache key from arbitrary parts."""
    raw = ':'.join(str(p) for p in ['palkay'] + list(parts))
    # Hash long keys to stay under Redis key size limits
    if len(raw) > 200:
        raw = 'palkay:h:' + hashlib.md5(raw.encode()).hexdigest()
    return raw


def product_cache_key(product_id):
    return cache_key('product', product_id)

def category_cache_key(slug):
    return cache_key('category', slug)

def brand_cache_key(slug):
    return cache_key('brand', slug)

def home_cache_key():
    return cache_key('home')

def nav_cache_key():
    return cache_key('nav', 'categories')


# ── Low-level get/set helpers ─────────────────────────────────────────────────

def get_cached(key, fetch_fn, ttl=300):
    """
    Generic cache-aside helper.
    Usage:
        data = get_cached('my-key', lambda: expensive_query(), ttl=600)
    """
    result = cache.get(key)
    if result is None:
        result = fetch_fn()
        if result is not None:
            cache.set(key, result, ttl)
    return result


# ── View-level cache decorator ───────────────────────────────────────────────

def cache_page_for(ttl, key_fn=None, vary_on_user=False):
    """
    Decorator that caches the full rendered response.

    Args:
        ttl: seconds to cache
        key_fn: callable(request) → string suffix for the cache key
        vary_on_user: if True, cache separately per authenticated user

    Usage:
        @cache_page_for(TTL_CATEGORY, key_fn=lambda r: r.GET.get('sort',''))
        def category_detail(request, slug): ...
    """
    def decorator(view_fn):
        @wraps(view_fn)
        def wrapper(request, *args, **kwargs):
            # Never cache for authenticated users on sensitive pages,
            # and never cache POST requests
            if request.method != 'GET':
                return view_fn(request, *args, **kwargs)

            # Build cache key
            parts = ['view', view_fn.__name__]
            parts += [str(v) for v in kwargs.values()]
            if key_fn:
                parts.append(key_fn(request))
            if vary_on_user and request.user.is_authenticated:
                parts.append(f'u:{request.user.pk}')

            key = cache_key(*parts)
            cached_response = cache.get(key)
            if cached_response is not None:
                logger.debug(f'Cache HIT: {key}')
                return cached_response

            response = view_fn(request, *args, **kwargs)
            # Only cache successful, complete responses
            if hasattr(response, 'render'):
                response.render()
            if response.status_code == 200:
                cache.set(key, response, ttl)
                logger.debug(f'Cache SET: {key} ttl={ttl}')
            return response
        return wrapper
    return decorator


# ── Cache invalidation via Django signals ─────────────────────────────────────

def invalidate_product_caches(product):
    """Wipe all cache keys related to a product."""
    keys = [
        product_cache_key(product.pk),
        category_cache_key(product.category.slug),
        home_cache_key(),
        cache_key('view', 'product_list'),
    ]
    cache.delete_many(keys)
    logger.info(f'Cache invalidated for product: {product.name}')


def invalidate_category_caches(category):
    keys = [
        category_cache_key(category.slug),
        nav_cache_key(),
        home_cache_key(),
    ]
    cache.delete_many(keys)
    logger.info(f'Cache invalidated for category: {category.name}')


def invalidate_home_cache():
    cache.delete(home_cache_key())


# ── Signal handlers ───────────────────────────────────────────────────────────

def _connect_signals():
    """
    Lazily connect signals to avoid circular import issues at module load.
    Call this from apps.py ready() or after Django setup.
    """
    try:
        from catalog.models import Product, Category, Brand

        @receiver(post_save, sender=Product)
        @receiver(post_delete, sender=Product)
        def on_product_change(sender, instance, **kwargs):
            invalidate_product_caches(instance)

        @receiver(post_save, sender=Category)
        @receiver(post_delete, sender=Category)
        def on_category_change(sender, instance, **kwargs):
            invalidate_category_caches(instance)

        @receiver(post_save, sender=Brand)
        @receiver(post_delete, sender=Brand)
        def on_brand_change(sender, instance, **kwargs):
            cache.delete(brand_cache_key(instance.slug))

    except Exception as e:
        logger.warning(f'Could not connect cache signals: {e}')


# ── HTTP cache headers helper ─────────────────────────────────────────────────

def set_public_cache_headers(response, max_age=300, s_maxage=None):
    """
    Set Cache-Control headers for public cacheable responses.
    s_maxage controls CDN (Cloudflare) TTL separately from browser.
    """
    kwargs = {
        'public': True,
        'max_age': max_age,
    }
    if s_maxage is not None:
        kwargs['s_maxage'] = s_maxage
    patch_cache_control(response, **kwargs)
    return response


def set_private_cache_headers(response):
    """Mark response as private — must not be cached by CDNs."""
    patch_cache_control(response, private=True, no_store=True)
    return response
