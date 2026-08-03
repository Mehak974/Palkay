from celery import shared_task
from django.utils import timezone
from .models import Order

@shared_task
def auto_cancel_pending_orders():
    """
    Cancel pending orders that have passed their 2-hour self-cancellation window.
    Transition them to CONFIRMED so fulfillment can begin.
    """
    orders = Order.objects.filter(
        status=Order.Status.PENDING,
        cancelled_by_user_until__lte=timezone.now()
    )
    
    count = 0
    for order in orders:
        order.update_status(
            new_status=Order.Status.CONFIRMED,
            note='Automatically confirmed after cancellation window expired.'
        )
        count += 1
        
    return f"Confirmed {count} orders."
