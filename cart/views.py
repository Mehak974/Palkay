from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction

from catalog.models import Product, ProductVariant
from orders.models import Coupon
from .models import Cart, CartItem


def cart_detail(request):
    """Shopping cart page."""
    cart = request.cart
    items = cart.items.select_related('product', 'variant').prefetch_related('product__images') if cart else []
    return render(request, 'cart/cart_detail.html', {
        'cart': cart,
        'items': items,
    })


@require_POST
def cart_add(request, product_id):
    """Add item to cart. Handles quantity update if already present."""
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    cart = request.cart
    variant_id = request.POST.get('variant_id')
    quantity = int(request.POST.get('quantity', 1))

    variant = None
    if variant_id:
        variant = get_object_or_404(ProductVariant, pk=variant_id, product=product)

    # Stock check
    stock = variant.stock_quantity if variant else product.stock_quantity
    if stock < quantity:
        messages.error(request, f'Only {stock} units available.')
        return redirect(product.get_absolute_url())

    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, variant=variant,
        defaults={'quantity': quantity}
    )
    if not created:
        new_qty = min(item.quantity + quantity, 100)
        if new_qty > stock:
            new_qty = stock
        item.quantity = new_qty
        item.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'ok',
            'cart_count': cart.total_items,
            'message': f'"{product.name}" added to cart.',
        })

    messages.success(request, f'"{product.name}" added to your cart.')
    return redirect('cart:detail')


@require_POST
def cart_update(request, item_id):
    """Update cart item quantity."""
    item = get_object_or_404(CartItem, pk=item_id, cart=request.cart)
    quantity = int(request.POST.get('quantity', 1))

    if quantity < 1:
        item.delete()
        messages.info(request, 'Item removed from cart.')
    else:
        stock = item.variant.stock_quantity if item.variant else item.product.stock_quantity
        item.quantity = min(quantity, stock, 100)
        item.save()

    return redirect('cart:detail')


@require_POST
def cart_remove(request, item_id):
    """Remove item from cart."""
    item = get_object_or_404(CartItem, pk=item_id, cart=request.cart)
    item.delete()
    messages.info(request, 'Item removed from cart.')
    return redirect('cart:detail')


def merge_guest_cart(request, user):
    """
    Called on login: merge guest session cart into user cart.
    Duplicate line items have quantities summed.
    """
    session_key = request.session.session_key
    if not session_key:
        return
    try:
        guest_cart = Cart.objects.get(session_key=session_key)
    except Cart.DoesNotExist:
        return

    user_cart, _ = Cart.objects.get_or_create(user=user)

    with transaction.atomic():
        for guest_item in guest_cart.items.all():
            existing = user_cart.items.filter(
                product=guest_item.product,
                variant=guest_item.variant
            ).first()
            if existing:
                existing.quantity = min(existing.quantity + guest_item.quantity, 100)
                existing.save()
            else:
                guest_item.cart = user_cart
                guest_item.save()
        guest_cart.delete()

@require_POST
def apply_coupon(request):
    """Apply a discount coupon to the cart."""
    code = request.POST.get('code', '').strip()
    cart = request.cart
    if not cart:
        return redirect('cart:detail')
    
    try:
        coupon = Coupon.objects.get(code__iexact=code, is_active=True)
        cart.coupon = coupon
        cart.save()
        messages.success(request, f'Coupon "{coupon.code}" applied successfully!')
    except Coupon.DoesNotExist:
        messages.error(request, 'Invalid or expired coupon code.')
        
    return redirect('cart:detail')

@require_POST
def remove_coupon(request):
    """Remove coupon from cart."""
    cart = request.cart
    if cart and cart.coupon:
        cart.coupon = None
        cart.save()
        messages.info(request, 'Coupon removed.')
    return redirect('cart:detail')
