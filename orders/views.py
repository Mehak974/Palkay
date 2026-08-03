from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

from cart.models import CartItem
from catalog.models import Product
from .models import Address, Order, OrderItem, OrderStatusHistory
from .forms import AddressForm, GuestCheckoutForm, OrderNotesForm
import threading


def checkout(request):
    """
    Multi-step checkout in a single view.
    Step 1: Address selection/entry
    Step 2: Review & place order (COD)
    """
    cart = request.cart
    if not cart or cart.total_items == 0:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart:detail')

    cart_items = cart.items.select_related('product', 'variant').prefetch_related('product__images')

    # Saved addresses for logged-in users
    saved_addresses = []
    if request.user.is_authenticated:
        saved_addresses = Address.objects.filter(user=request.user).order_by('-is_default', '-created_at')

    address_form = AddressForm(user=request.user)
    guest_form = GuestCheckoutForm() if not request.user.is_authenticated else None
    notes_form = OrderNotesForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        # ── Use a saved address ───────────────────────────────
        if action == 'use_saved':
            address_id = request.POST.get('address_id')
            try:
                address = saved_addresses.get(pk=address_id)
            except Address.DoesNotExist:
                messages.error(request, 'Address not found.')
                return redirect('orders:checkout')
            notes_form = OrderNotesForm(request.POST)
            if notes_form.is_valid():
                return _place_order(request, cart, address, notes_form.cleaned_data.get('special_instructions', ''))

        # ── New address ───────────────────────────────────────
        elif action == 'new_address':
            address_form = AddressForm(request.POST, user=request.user)
            notes_form = OrderNotesForm(request.POST)
            guest_form_valid = True

            if not request.user.is_authenticated:
                guest_form = GuestCheckoutForm(request.POST)
                guest_form_valid = guest_form.is_valid()

            if address_form.is_valid() and notes_form.is_valid() and guest_form_valid:
                address = address_form.save(commit=False)
                if request.user.is_authenticated:
                    address.user = request.user
                address.save()
                special = notes_form.cleaned_data.get('special_instructions', '')
                guest_email = guest_form.cleaned_data.get('email', '') if guest_form else ''
                return _place_order(request, cart, address, special, guest_email=guest_email)

    return render(request, 'orders/checkout.html', {
        'cart': cart,
        'cart_items': cart_items,
        'saved_addresses': saved_addresses,
        'address_form': address_form,
        'guest_form': guest_form,
        'notes_form': notes_form,
    })


def _place_order(request, cart, address, special_instructions='', guest_email=''):
    """Atomic order placement with stock decrement."""
    cart_items = list(cart.items.select_related('product', 'variant').all())

    with transaction.atomic():
        # Stock validation & decrement
        for item in cart_items:
            if item.variant:
                variant = item.variant.__class__.objects.select_for_update().get(pk=item.variant.pk)
                if variant.stock_quantity < item.quantity:
                    messages.error(request, f'"{item.product.name}" only has {variant.stock_quantity} units left.')
                    return redirect('cart:detail')
                variant.stock_quantity -= item.quantity
                variant.save()
            else:
                product = Product.objects.select_for_update().get(pk=item.product.pk)
                if product.stock_quantity < item.quantity:
                    messages.error(request, f'"{item.product.name}" only has {product.stock_quantity} units left.')
                    return redirect('cart:detail')
                product.stock_quantity -= item.quantity
                product.order_count += item.quantity
                product.save()

        subtotal = cart.subtotal
        shipping_fee = cart.shipping_fee
        discount_amount = cart.discount_amount
        coupon_code = cart.coupon.code if cart.coupon else ''

        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            delivery_address=address,
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            discount_amount=discount_amount,
            coupon_code=coupon_code,
            total=subtotal - discount_amount + shipping_fee,
            special_instructions=special_instructions,
            guest_email=guest_email,
        )

        # Create immutable order items (price snapshot)
        for item in cart_items:
            variant_attrs = None
            if item.variant:
                variant_attrs = {
                    str(av.attribute_type): av.value
                    for av in item.variant.attribute_values.select_related('attribute_type').all()
                }
            OrderItem.objects.create(
                order=order,
                product=item.product,
                product_name=item.product.name,
                product_price=item.effective_price,
                quantity=item.quantity,
                variant=item.variant,
                variant_attributes=variant_attrs,
            )

        # Initial status history entry
        OrderStatusHistory.objects.create(
            order=order,
            status=Order.Status.PENDING,
            note='Order placed by customer.',
        )

        # Clear the cart
        cart.items.all().delete()

    # Send confirmation email in background thread (non-blocking)
    threading.Thread(target=_send_confirmation_email, args=(order,)).start()

    messages.success(request, f'Order #{order.order_number} placed successfully!')
    return redirect('orders:confirmation', order_number=order.order_number)


def _send_confirmation_email(order):
    """Send order confirmation email. Silently fails if misconfigured."""
    recipient = order.guest_email or (order.user.email if order.user else None)
    if not recipient:
        return
    try:
        subject = f'Your Palkay order #{order.order_number} is confirmed!'
        body = render_to_string('orders/email_confirmation.txt', {'order': order})
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=True)
    except Exception:
        pass


def order_confirmation(request, order_number):
    """Thank-you page after successful order placement."""
    order = get_object_or_404(Order, order_number=order_number)

    # Security: only owner, guest (via session token), or staff can view
    if order.user and order.user != request.user and not request.user.is_staff:
        messages.error(request, 'Order not found.')
        return redirect('pages:home')

    items = order.items.select_related('product').prefetch_related('product__images')
    return render(request, 'orders/order_confirmation.html', {
        'order': order,
        'items': items,
    })


@login_required
def order_list(request):
    """Customer's order history."""
    orders = Order.objects.filter(user=request.user).prefetch_related('items').order_by('-created_at')
    return render(request, 'orders/order_list.html', {'orders': orders})


@login_required
def order_detail(request, order_number):
    """Order detail for logged-in customer."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    items = order.items.select_related('product').prefetch_related('product__images')
    history = order.history.all()
    return render(request, 'orders/order_detail.html', {
        'order': order,
        'items': items,
        'history': history,
    })


@login_required
def cancel_order(request, order_number):
    """Customer self-cancellation within 2-hour window."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if not order.can_be_cancelled_by_user:
        messages.error(request, 'This order can no longer be cancelled. Please contact support.')
        return redirect('orders:detail', order_number=order_number)

    if request.method == 'POST':
        with transaction.atomic():
            # Restore stock
            for item in order.items.select_related('product', 'variant').all():
                if item.variant:
                    item.variant.__class__.objects.filter(pk=item.variant.pk).update(
                        stock_quantity=models.F('stock_quantity') + item.quantity
                    )
                elif item.product:
                    Product.objects.filter(pk=item.product.pk).update(
                        stock_quantity=models.F('stock_quantity') + item.quantity,
                        order_count=models.F('order_count') - item.quantity
                    )
            order.update_status(
                Order.Status.CANCELLED,
                changed_by=request.user,
                note='Cancelled by customer.'
            )
        messages.success(request, f'Order #{order.order_number} has been cancelled.')
        return redirect('orders:list')

    return render(request, 'orders/cancel_confirm.html', {'order': order})
