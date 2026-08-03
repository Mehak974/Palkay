import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import timedelta
from catalog.models import Product, ProductVariant


class Address(models.Model):
    """
    Delivery address book. Supports both registered users (nullable FK)
    and guest checkouts (user=NULL).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='addresses'
    )
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=50, default='Austin')
    state = models.CharField(max_length=2, default='TX')
    zip_code = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f'{self.full_name}, {self.address_line_1}, {self.city}, {self.state}'

    def save(self, *args, **kwargs):
        if self.is_default and self.user:
            # Unset other defaults for this user
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Order(models.Model):
    """
    Customer order record. COD only in Phase 1.
    UUID PK prevents enumeration. Status managed via OrderStatusHistory.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        OUT_FOR_DELIVERY = 'OUT_FOR_DELIVERY', 'Out for Delivery'
        DELIVERED = 'DELIVERED', 'Delivered'
        CANCELLED = 'CANCELLED', 'Cancelled'
        RETURNED = 'RETURNED', 'Returned'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='orders'
    )
    delivery_address = models.ForeignKey(
        Address, on_delete=models.PROTECT, related_name='orders'
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, default='COD', editable=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    special_instructions = models.TextField(blank=True)
    guest_email = models.EmailField(blank=True, help_text='For guest orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_by_user_until = models.DateTimeField(null=True, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        if not self.cancelled_by_user_until:
            hours = getattr(settings, 'ORDER_CANCEL_WINDOW_HOURS', 2)
            self.cancelled_by_user_until = timezone.now() + timedelta(hours=hours)
        super().save(*args, **kwargs)

    def _generate_order_number(self):
        import random
        import string
        prefix = 'PLK'
        suffix = ''.join(random.choices(string.digits, k=8))
        return f'{prefix}{suffix}'

    @property
    def can_be_cancelled_by_user(self):
        return (
            self.status == self.Status.PENDING and
            timezone.now() < self.cancelled_by_user_until
        )

    def update_status(self, new_status, changed_by=None, note='', expected_delivery=None):
        self.status = new_status
        self.save()
        OrderStatusHistory.objects.create(
            order=self,
            status=new_status,
            changed_by=changed_by,
            note=note,
            expected_delivery=expected_delivery,
        )


class OrderItem(models.Model):
    """
    Immutable line item with price snapshot.
    product_name and product_price never change after creation.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)      # snapshot
    product_price = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.SET_NULL, null=True, blank=True
    )
    variant_attributes = models.JSONField(null=True, blank=True)  # audit snapshot

    def __str__(self):
        return f'{self.quantity}× {self.product_name} (Order {self.order.order_number})'

    def save(self, *args, **kwargs):
        self.line_total = self.product_price * self.quantity
        super().save(*args, **kwargs)


class OrderStatusHistory(models.Model):
    """Immutable append-only audit log of all order status changes."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(max_length=20, choices=Order.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)
    expected_delivery = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-changed_at']
        verbose_name_plural = 'Order status history'

    def __str__(self):
        return f'{self.order.order_number} → {self.status} at {self.changed_at}'
