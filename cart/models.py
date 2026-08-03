from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from catalog.models import Product, ProductVariant
from orders.models import Coupon


class Cart(models.Model):
    """
    Shopping cart. Supports both registered users and guest sessions.
    One cart per user. Guest carts keyed by Django session.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='cart'
    )
    session_key = models.CharField(max_length=40, unique=True, null=True, blank=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(user__isnull=False),
                name='unique_user_cart'
            ),
            models.UniqueConstraint(
                fields=['session_key'],
                condition=models.Q(session_key__isnull=False),
                name='unique_session_cart'
            ),
        ]

    def __str__(self):
        if self.user:
            return f'Cart for {self.user.email}'
        return f'Guest cart ({self.session_key})'

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items.all())

    @property
    def shipping_fee(self):
        threshold = getattr(settings, 'FREE_SHIPPING_THRESHOLD', 200)
        if self.subtotal >= threshold:
            return 0
        return 10  # flat shipping fee

    @property
    def discount_amount(self):
        if self.coupon and self.coupon.is_active:
            return (self.subtotal * self.coupon.discount_percent) / 100
        return 0

    @property
    def total(self):
        return self.subtotal - self.discount_amount + self.shipping_fee

    def get_or_create_item(self, product, variant=None):
        """Return existing cart item or create a new one."""
        item, created = self.items.get_or_create(
            product=product,
            variant=variant,
            defaults={'quantity': 1}
        )
        return item, created


class CartItem(models.Model):
    """Individual line item in a cart."""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    quantity = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('cart', 'product', 'variant')]

    def __str__(self):
        return f'{self.quantity}× {self.product.name}'

    @property
    def effective_price(self):
        if self.variant and self.variant.price_override:
            return self.variant.price_override
        return self.product.price

    @property
    def line_total(self):
        return self.effective_price * self.quantity
