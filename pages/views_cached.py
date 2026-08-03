"""
Pages views with homepage caching applied.
Replaces pages/views.py.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.db.models import Prefetch

from catalog.models import Product, Category, Brand, ProductImage
from pages.models import Page, ContactSubmission
from palkay.cache import (
    get_cached, set_public_cache_headers, home_cache_key, TTL_HOME, TTL_CMS
)


def home(request):
    """
    Homepage. For anonymous users we serve cached data; the rendered
    HTML itself gets public Cache-Control so Cloudflare can edge-cache it.
    Authenticated users always get a fresh response (personalised nav, cart).
    """

    def _fetch_home_data():
        return {
            'featured_products': list(
                Product.objects
                .filter(is_active=True, is_featured=True)
                .select_related('category', 'brand')
                .prefetch_related(
                    Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True), to_attr='primary_images')
                )
                .order_by('-created_at')[:6]
            ),
            'new_arrivals': list(
                Product.objects
                .filter(is_active=True)
                .select_related('category', 'brand')
                .prefetch_related(
                    Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True), to_attr='primary_images')
                )
                .order_by('-created_at')[:5]
            ),
            'best_sellers': list(
                Product.objects
                .filter(is_active=True)
                .prefetch_related(
                    Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True), to_attr='primary_images')
                )
                .order_by('-order_count')[:4]
            ),
            'categories': list(
                Category.objects
                .filter(is_active=True, parent__isnull=True)
                .order_by('sort_order')[:6]
            ),
            'brands': list(Brand.objects.filter(is_active=True)),
        }

    data = get_cached(home_cache_key(), _fetch_home_data, ttl=TTL_HOME)

    response = render(request, 'pages/home.html', data)

    # Let Cloudflare cache the homepage for anonymous visitors
    if not request.user.is_authenticated:
        set_public_cache_headers(response, max_age=60, s_maxage=TTL_HOME)

    return response


@never_cache
def contact(request):
    """Contact page — never cached (has a live form)."""
    if request.method == 'POST':
        name    = request.POST.get('name', '').strip()
        email   = request.POST.get('email', '').strip()
        phone   = request.POST.get('phone', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        errors = []
        if not name:
            errors.append('Name is required.')
        if not email:
            errors.append('Email is required.')
        if not message or len(message) < 10:
            errors.append('Message must be at least 10 characters.')

        if not errors:
            ContactSubmission.objects.create(
                name=name, email=email, phone=phone,
                subject=subject, message=message,
            )
            messages.success(request, "Thanks for reaching out! We'll get back to you within 24 hours.")
            return redirect('pages:contact')
        else:
            for err in errors:
                messages.error(request, err)

    return render(request, 'pages/contact.html')


def cms_page(request, slug):
    """CMS pages — long cache, invalidated on admin save."""
    page = get_object_or_404(Page, slug=slug, is_published=True)
    response = render(request, 'pages/cms_page.html', {'page': page})
    set_public_cache_headers(response, max_age=300, s_maxage=TTL_CMS)
    return response


def about(request):
    response = render(request, 'pages/about.html')
    set_public_cache_headers(response, max_age=300, s_maxage=TTL_CMS)
    return response
