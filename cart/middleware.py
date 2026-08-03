from .models import Cart


class CartMiddleware:
    """
    Attaches the current cart object to every request.
    Used by the cart context processor and views.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.cart = self._get_cart(request)
        response = self.get_response(request)
        return response

    def _get_cart(self, request):
        if request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user)
            return cart
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            cart, _ = Cart.objects.get_or_create(session_key=session_key)
            return cart
