"""
Palkay Query Optimisation
--------------------------
Custom managers and querysets with pre-built select_related /
prefetch_related chains. Import these in views for zero-N+1 queries.

Usage:
    from palkay.querysets import optimised_products, optimised_cart
"""

from django.db.models import Prefetch


def optimised_products(qs=None):
    """
    Returns a fully optimised Product queryset.
    Fetches category, brand, and primary image in 3 queries total.
    """
    from catalog.models import Product, ProductImage

    if qs is None:
        qs = Product.objects.filter(is_active=True)

    return qs.select_related(
        'category',
        'category__parent',
        'brand',
    ).prefetch_related(
        Prefetch(
            'images',
            queryset=ProductImage.objects.filter(is_primary=True),
            to_attr='primary_images'
        )
    )


def optimised_products_full(qs=None):
    """
    Full product queryset including all images and variants.
    Use for product detail pages only — heavier than optimised_products.
    """
    from catalog.models import Product, ProductImage

    if qs is None:
        qs = Product.objects.filter(is_active=True)

    return qs.select_related(
        'category',
        'category__parent',
        'brand',
    ).prefetch_related(
        'images',
        'variants',
        'variants__attribute_values',
        'variants__attribute_values__attribute_type',
    )


def optimised_cart(cart):
    """
    Returns cart items with all related data pre-fetched.
    Avoids N+1 on cart page and checkout summary.
    """
    from cart.models import CartItem

    return (
        cart.items
        .select_related(
            'product',
            'product__category',
            'product__brand',
            'variant',
        )
        .prefetch_related(
            Prefetch(
                'product__images',
                queryset=__import__(
                    'catalog.models', fromlist=['ProductImage']
                ).ProductImage.objects.filter(is_primary=True),
                to_attr='primary_images'
            ),
            'variant__attribute_values',
            'variant__attribute_values__attribute_type',
        )
    )


def optimised_orders(qs=None):
    """
    Optimised order queryset for order list views.
    """
    from orders.models import Order

    if qs is None:
        qs = Order.objects.all()

    return qs.select_related(
        'user',
        'delivery_address',
    ).prefetch_related(
        'items',
    )


def optimised_order_detail(order_number, user=None):
    """
    Single order with full item detail — for order detail page.
    """
    from orders.models import Order, OrderItem
    from catalog.models import ProductImage

    qs = Order.objects.filter(order_number=order_number)
    if user:
        qs = qs.filter(user=user)

    return qs.select_related(
        'user',
        'delivery_address',
    ).prefetch_related(
        Prefetch(
            'items',
            queryset=OrderItem.objects.select_related('product', 'variant').prefetch_related(
                Prefetch(
                    'product__images',
                    queryset=ProductImage.objects.filter(is_primary=True),
                    to_attr='primary_images'
                )
            )
        ),
        'history',
        'history__changed_by',
    ).first()
