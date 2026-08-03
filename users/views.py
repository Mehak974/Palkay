from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from cart.views import merge_guest_cart
from pages.models import Wishlist
from orders.models import Address
from .forms import LoginForm, RegisterForm, ProfileForm, CustomPasswordChangeForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect('users:dashboard')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        merge_guest_cart(request, user)
        login(request, user)
        next_url = request.GET.get('next', 'users:dashboard')
        messages.success(request, f'Welcome back, {user.get_short_name()}!')
        return redirect(next_url)

    return render(request, 'users/login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('users:dashboard')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        merge_guest_cart(request, user)
        login(request, user)
        messages.success(request, f'Welcome to Palkay, {user.get_short_name()}!')
        return redirect('users:dashboard')

    return render(request, 'users/register.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been signed out.')
    return redirect('pages:home')


@login_required
def dashboard(request):
    """Account dashboard — overview, orders, addresses, wishlist."""
    all_orders = request.user.orders.order_by('-created_at')
    recent_orders = all_orders[:5]
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product').prefetch_related('product__images')
    addresses = Address.objects.filter(user=request.user)
    
    from orders.forms import AddressForm
    address_form = AddressForm(user=request.user)
    
    return render(request, 'users/dashboard.html', {
        'recent_orders': recent_orders,
        'all_orders': all_orders,
        'wishlist_items': wishlist_items,
        'wishlist_count': wishlist_items.count(),
        'addresses': addresses,
        'address_count': addresses.count(),
        'address_form': address_form,
    })


@login_required
def profile_edit(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated.')
        return redirect('users:dashboard')
    return render(request, 'users/profile_edit.html', {'form': form})


@login_required
def change_password(request):
    form = CustomPasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Password changed successfully.')
        return redirect('users:dashboard')
    return render(request, 'users/change_password.html', {'form': form})


@login_required
def wishlist(request):
    items = Wishlist.objects.filter(user=request.user).select_related('product').prefetch_related('product__images')
    return render(request, 'users/wishlist.html', {'items': items})


@login_required
def address_list(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'users/address_list.html', {'addresses': addresses})


@login_required
def address_add(request):
    from orders.forms import AddressForm
    from django.http import JsonResponse
    form = AddressForm(request.POST or None, user=request.user)
    if request.method == 'POST':
        if form.is_valid():
            addr = form.save(commit=False)
            addr.user = request.user
            addr.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'id': addr.pk, 'full_name': addr.full_name, 'address_line1': addr.address_line1, 'city': addr.city, 'state': addr.state, 'postal_code': addr.postal_code, 'country': addr.country})
            messages.success(request, 'Address saved.')
            return redirect('users:dashboard')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    return render(request, 'users/address_form.html', {'form': form, 'title': 'Add Address'})


@login_required
def address_edit(request, pk):
    from orders.forms import AddressForm
    from django.http import JsonResponse
    address = get_object_or_404(Address, pk=pk, user=request.user)
    form = AddressForm(request.POST or None, instance=address, user=request.user)
    if request.method == 'POST':
        if form.is_valid():
            addr = form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'id': addr.pk, 'full_name': addr.full_name, 'address_line1': addr.address_line1, 'city': addr.city, 'state': addr.state, 'postal_code': addr.postal_code, 'country': addr.country})
            messages.success(request, 'Address updated.')
            return redirect('users:dashboard')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    return render(request, 'users/address_form.html', {'form': form, 'title': 'Edit Address'})


@login_required
@require_POST
def address_delete(request, pk):
    from django.http import JsonResponse
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if address.orders.exists():
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Cannot delete an address linked to existing orders.'}, status=400)
        messages.error(request, 'Cannot delete an address linked to existing orders.')
    else:
        address.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success'})
        messages.success(request, 'Address removed.')
    return redirect('users:dashboard')
