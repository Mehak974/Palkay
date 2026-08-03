from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from .models import Product, Category, Brand
from pages.models import Wishlist


def product_list(request):
    """All products with filtering and sorting."""
    qs = Product.objects.filter(is_active=True, images__isnull=False).distinct().select_related('category', 'brand').prefetch_related('images')

    category_slug = request.GET.get('category')
    brand_slug = request.GET.get('brand')
    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', '-created_at')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    active_category = None
    active_brand = None

    if category_slug:
        active_category = get_object_or_404(Category, slug=category_slug, is_active=True)
        # Include subcategory products
        cat_ids = [active_category.pk] + list(active_category.children.values_list('pk', flat=True))
        qs = qs.filter(category__in=cat_ids)

    if brand_slug:
        active_brand = get_object_or_404(Brand, slug=brand_slug, is_active=True)
        qs = qs.filter(brand=active_brand)

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(sku__icontains=q))

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
        '-created_at': 'Newest First',
        'price': 'Price: Low → High',
        '-price': 'Price: High → Low',
        '-order_count': 'Best Selling',
        '-view_count': 'Most Popular',
    }
    if sort not in SORT_OPTIONS:
        sort = '-created_at'
    qs = qs.order_by(sort)

    paginator = Paginator(qs, 24)
    page_obj = paginator.get_page(request.GET.get('page'))

    categories = Category.objects.filter(is_active=True, parent__isnull=True).order_by('sort_order')
    brands = Brand.objects.filter(is_active=True)

    return render(request, 'catalog/product_list.html', {
        'page_obj': page_obj,
        'categories': categories,
        'brands': brands,
        'active_category': active_category,
        'active_brand': active_brand,
        'query': q,
        'sort': sort,
        'sort_options': SORT_OPTIONS,
        'total_count': qs.count(),
    })


def product_detail(request, slug):
    """Product detail page with variant handling."""
    product = get_object_or_404(
        Product.objects.select_related('category', 'brand').prefetch_related(
            'images', 'variants__attribute_values__attribute_type'
        ),
        slug=slug, is_active=True
    )
    product.increment_view()

    related = Product.objects.filter(
        category=product.category, is_active=True, images__isnull=False
    ).distinct().exclude(pk=product.pk).select_related('brand').prefetch_related('images')[:4]

    # Wishlist state
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()

    reviews = product.reviews.filter(is_approved=True)
    from .forms import ReviewForm
    review_form = ReviewForm()

    return render(request, 'catalog/product_detail.html', {
        'product': product,
        'related_products': related,
        'in_wishlist': in_wishlist,
        'reviews': reviews,
        'review_form': review_form,
    })

@login_required
@require_POST
def add_review(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    from .forms import ReviewForm
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.user = request.user
        review.save()
        messages.success(request, 'Your review has been submitted!')
    else:
        messages.error(request, 'There was an error submitting your review.')
    return redirect(product.get_absolute_url())


def category_detail(request, slug):
    """Category landing page — delegates to product_list with filter."""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    cat_ids = [category.pk] + list(category.children.values_list('pk', flat=True))
    qs = Product.objects.filter(
        category__in=cat_ids, is_active=True, images__isnull=False
    ).distinct().select_related('category', 'brand').prefetch_related('images')

    sort = request.GET.get('sort', '-created_at')
    qs = qs.order_by(sort)

    paginator = Paginator(qs, 24)
    page_obj = paginator.get_page(request.GET.get('page'))

    SORT_OPTIONS = {
        '-created_at': 'Newest First',
        'price': 'Price: Low → High',
        '-price': 'Price: High → Low',
        '-order_count': 'Best Selling',
    }

    return render(request, 'catalog/category_detail.html', {
        'category': category,
        'page_obj': page_obj,
        'sort': sort,
        'sort_options': SORT_OPTIONS,
    })


def brand_detail(request, slug):
    """Brand landing page."""
    brand = get_object_or_404(Brand, slug=slug, is_active=True)
    qs = Product.objects.filter(
        brand=brand, is_active=True, images__isnull=False
    ).distinct().select_related('category').prefetch_related('images').order_by('-created_at')

    paginator = Paginator(qs, 24)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'catalog/brand_detail.html', {
        'brand': brand,
        'page_obj': page_obj,
    })


def search(request):
    """Search redirect — delegates to product_list with ?q="""
    q = request.GET.get('q', '').strip()
    if q:
        return redirect(f'/products/?q={q}')
    return redirect('catalog:product_list')


@login_required
@require_POST
def toggle_wishlist(request, product_id):
    """Add/remove product from wishlist. Returns JSON for AJAX."""
    from catalog.models import Product as P
    product = get_object_or_404(P, pk=product_id, is_active=True)
    obj, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        obj.delete()
        return JsonResponse({'status': 'removed'})
    return JsonResponse({'status': 'added'})
