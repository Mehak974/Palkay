"""
Catalog views with view-level caching applied.
Replaces catalog/views.py — drop this in as the new version.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Prefetch
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required

from catalog.models import Product, Category, Brand, ProductImage
from pages.models import Wishlist
from palkay.cache import (
    cache_page_for, get_cached, set_public_cache_headers, set_private_cache_headers,
    TTL_HOME, TTL_PRODUCT, TTL_CATEGORY, TTL_BRAND, nav_cache_key
)
from django.core.cache import cache


def _get_wishlist_ids(user):
    """Return set of product PKs in user's wishlist (for template rendering)."""
    if not user.is_authenticated:
        return set()
    key = f'palkay:wishlist:{user.pk}'
    ids = cache.get(key)
    if ids is None:
        ids = set(Wishlist.objects.filter(user=user).values_list('product_id', flat=True))
        cache.set(key, ids, 60 * 5)
    return ids


def _invalidate_wishlist_cache(user):
    cache.delete(f'palkay:wishlist:{user.pk}')


# ── Product List ──────────────────────────────────────────────────────────────

def product_list(request):
    """
    All products with filtering, sorting, pagination.
    Not cached at view level (too many filter permutations) — relies on
    query-level caching and DB connection pooling for speed.
    """
    qs = (
        Product.objects
        .filter(is_active=True)
        .select_related('category', 'brand')
        .prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True), to_attr='primary_images')
        )
    )

    category_slug = request.GET.get('category')
    brand_slug    = request.GET.get('brand')
    q             = request.GET.get('q', '').strip()
    sort          = request.GET.get('sort', '-created_at')
    min_price     = request.GET.get('min_price')
    max_price     = request.GET.get('max_price')

    active_category = None
    active_brand    = None

    if category_slug:
        active_category = get_object_or_404(Category, slug=category_slug, is_active=True)
        cat_ids = [active_category.pk] + list(
            active_category.children.values_list('pk', flat=True)
        )
        qs = qs.filter(category__in=cat_ids)

    if brand_slug:
        active_brand = get_object_or_404(Brand, slug=brand_slug, is_active=True)
        qs = qs.filter(brand=active_brand)

    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(description__icontains=q) | Q(sku__icontains=q)
        )

    if min_price:
        try:
            qs = qs.filter(price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            qs = qs.filter(price__lte=float(max_price))
        except ValueError:
            pass

    SORT_OPTIONS = {
        '-created_at':  'Newest First',
        'price':        'Price: Low → High',
        '-price':       'Price: High → Low',
        '-order_count': 'Best Selling',
        '-view_count':  'Most Popular',
    }
    if sort not in SORT_OPTIONS:
        sort = '-created_at'
    qs = qs.order_by(sort)

    paginator = Paginator(qs, 24)
    page_obj  = paginator.get_page(request.GET.get('page'))

    # Cached nav data
    categories = get_cached(
        nav_cache_key(),
        lambda: list(Category.objects.filter(is_active=True, parent__isnull=True).order_by('sort_order')),
        ttl=3600
    )
    brands = list(Brand.objects.filter(is_active=True))

    response = render(request, 'catalog/product_list.html', {
        'page_obj':        page_obj,
        'categories':      categories,
        'brands':          brands,
        'active_category': active_category,
        'active_brand':    active_brand,
        'query':           q,
        'sort':            sort,
        'sort_options':    SORT_OPTIONS,
        'total_count':     paginator.count,
        'wishlist_ids':    _get_wishlist_ids(request.user),
    })
    return response


# ── Product Detail ────────────────────────────────────────────────────────────

def product_detail(request, slug):
    """
    Product detail — cached for anonymous users; always fresh for logged-in
    (so wishlist heart state is accurate).
    """
    product = get_object_or_404(
        Product.objects
        .select_related('category', 'brand')
        .prefetch_related(
            'images',
            'variants__attribute_values__attribute_type',
        ),
        slug=slug, is_active=True
    )
    product.increment_view()

    related = list(
        Product.objects
        .filter(category=product.category, is_active=True)
        .exclude(pk=product.pk)
        .select_related('brand')
        .prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True), to_attr='primary_images')
        )[:4]
    )

    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = product.pk in _get_wishlist_ids(request.user)

    response = render(request, 'catalog/product_detail.html', {
        'product':          product,
        'related_products': related,
        'in_wishlist':      in_wishlist,
        'wishlist_ids':     _get_wishlist_ids(request.user),
    })

    # Public cache headers for Cloudflare (anonymous visits)
    if not request.user.is_authenticated:
        set_public_cache_headers(response, max_age=60, s_maxage=TTL_PRODUCT)
    else:
        set_private_cache_headers(response)

    return response


# ── Category Detail ───────────────────────────────────────────────────────────

@cache_page_for(TTL_CATEGORY, key_fn=lambda r: f"{r.GET.get('sort','')}_p{r.GET.get('page','1')}")
def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    cat_ids  = [category.pk] + list(category.children.values_list('pk', flat=True))
    qs = (
        Product.objects
        .filter(category__in=cat_ids, is_active=True)
        .select_related('category', 'brand')
        .prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True), to_attr='primary_images')
        )
    )

    SORT_OPTIONS = {
        '-created_at':  'Newest First',
        'price':        'Price: Low → High',
        '-price':       'Price: High → Low',
        '-order_count': 'Best Selling',
    }
    sort = request.GET.get('sort', '-created_at')
    if sort not in SORT_OPTIONS:
        sort = '-created_at'
    qs = qs.order_by(sort)

    paginator = Paginator(qs, 24)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'catalog/category_detail.html', {
        'category':     category,
        'page_obj':     page_obj,
        'sort':         sort,
        'sort_options': SORT_OPTIONS,
        'wishlist_ids': _get_wishlist_ids(request.user),
    })


# ── Brand Detail ──────────────────────────────────────────────────────────────

@cache_page_for(TTL_BRAND, key_fn=lambda r: r.GET.get('page', '1'))
def brand_detail(request, slug):
    brand = get_object_or_404(Brand, slug=slug, is_active=True)
    qs = (
        Product.objects
        .filter(brand=brand, is_active=True)
        .select_related('category')
        .prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True), to_attr='primary_images')
        )
        .order_by('-created_at')
    )
    paginator = Paginator(qs, 24)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'catalog/brand_detail.html', {
        'brand':        brand,
        'page_obj':     page_obj,
        'wishlist_ids': _get_wishlist_ids(request.user),
    })


# ── Search ────────────────────────────────────────────────────────────────────

def search(request):
    q = request.GET.get('q', '').strip()
    if q:
        return redirect(f'/products/?q={q}')
    return redirect('catalog:product_list')


# ── Wishlist Toggle ───────────────────────────────────────────────────────────

@never_cache
@login_required
@require_POST
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    obj, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        obj.delete()
        _invalidate_wishlist_cache(request.user)
        return JsonResponse({'status': 'removed'})
    _invalidate_wishlist_cache(request.user)
    return JsonResponse({'status': 'added'})
