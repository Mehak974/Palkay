from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.http import require_GET

from catalog.models import Product, Category, Brand
from .models import Page, ContactSubmission


@require_GET
def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")






def home(request):
    """Homepage with featured products, categories, new arrivals."""
    hero_product = Product.objects.filter(is_active=True, slug='gummies', images__isnull=False).distinct().prefetch_related('images').first()
    if not hero_product:
        hero_product = Product.objects.filter(
            is_active=True, is_featured=True, images__isnull=False
        ).distinct().prefetch_related('images').first()

    featured_products = Product.objects.filter(
        is_active=True, is_featured=True, images__isnull=False
    ).distinct().select_related('category', 'brand').prefetch_related('images').order_by('-created_at')[:6]

    new_arrivals = Product.objects.filter(
        is_active=True, category__name='Home & Decor', images__isnull=False
    ).distinct().select_related('category', 'brand').prefetch_related('images').order_by('-created_at')[:5]

    categories = Category.objects.filter(
        is_active=True, parent__isnull=True
    ).exclude(slug='uncategorized').prefetch_related('children')

    brands = Brand.objects.filter(is_active=True)

    best_sellers = Product.objects.filter(
        is_active=True, images__isnull=False
    ).distinct().exclude(sku__startswith='DUM-').order_by('-order_count').prefetch_related('images')[:4]

    return render(request, 'pages/home.html', {
        'hero_product': hero_product,
        'featured_products': featured_products,
        'new_arrivals': new_arrivals,
        'categories': categories,
        'brands': brands,
        'best_sellers': best_sellers,
    })


def contact(request):
    """Contact page with form submission."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
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
    """Render a CMS-managed page."""
    page = get_object_or_404(Page, slug=slug, is_published=True)
    context = {'page': page}
    if slug == 'faq':
        import re
        pairs = re.findall(r'<h3>(.*?)</h3>\s*<p>(.*?)</p>', page.content, re.DOTALL)
        context['faq_items'] = [{'question': q.strip(), 'answer': a.strip()} for q, a in pairs]
    return render(request, 'pages/cms_page.html', context)


def about(request):
    return render(request, 'pages/about.html')
