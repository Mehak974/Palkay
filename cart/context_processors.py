def cart_context(request):
    """Inject cart into every template context."""
    cart = getattr(request, 'cart', None)
    return {
        'cart': cart,
        'cart_count': cart.total_items if cart else 0,
    }
