from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from catalog.models import Product, Category
from orders.models import Order
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

@staff_member_required
def dashboard(request):
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    total_revenue = Order.objects.filter(
        created_at__gte=thirty_days_ago, status__in=['processing', 'shipped', 'delivered']
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    total_orders = Order.objects.filter(created_at__gte=thirty_days_ago).count()
    
    popular_products = Product.objects.order_by('-view_count')[:5]
    best_sellers = Product.objects.order_by('-order_count')[:5]

    return render(request, 'analytics/dashboard.html', {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'popular_products': popular_products,
        'best_sellers': best_sellers,
    })
