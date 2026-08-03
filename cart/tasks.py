from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from .models import Cart

@shared_task
def cleanup_expired_carts():
    """
    Delete guest carts that have expired (older than CART_EXPIRY_DAYS).
    """
    expiry_days = getattr(settings, 'CART_EXPIRY_DAYS', 30)
    cutoff = timezone.now() - timedelta(days=expiry_days)
    
    # Delete carts without a user that haven't been updated since cutoff
    expired_carts = Cart.objects.filter(
        user__isnull=True,
        updated_at__lte=cutoff
    )
    
    count, _ = expired_carts.delete()
    return f"Deleted {count} expired guest carts."
