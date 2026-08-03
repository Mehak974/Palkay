from django.contrib import admin
from django.utils.html import format_html
from .models import Address, Order, OrderItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'product_price', 'quantity', 'line_total')
    can_delete = False


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ('status', 'changed_by', 'changed_at', 'note')
    can_delete = False
    ordering = ('-changed_at',)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'city', 'state', 'zip_code', 'is_default')
    list_filter = ('state', 'is_default')
    search_fields = ('full_name', 'address_line_1', 'zip_code')
    raw_id_fields = ('user',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user_display', 'total', 'status', 'payment_method', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('order_number', 'user__email', 'guest_email', 'delivery_address__full_name')
    readonly_fields = ('id', 'order_number', 'created_at', 'updated_at', 'cancelled_by_user_until')
    inlines = [OrderItemInline, OrderStatusHistoryInline]
    ordering = ('-created_at',)

    fieldsets = (
        ('Order', {'fields': ('id', 'order_number', 'user', 'guest_email', 'delivery_address')}),
        ('Financials', {'fields': ('subtotal', 'shipping_fee', 'total', 'payment_method')}),
        ('Status', {'fields': ('status', 'special_instructions', 'expected_delivery_date')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at', 'cancelled_by_user_until')}),
    )

    def user_display(self, obj):
        if obj.user:
            return obj.user.email
        return obj.guest_email or '—'
    user_display.short_description = 'Customer'

    actions = ['mark_confirmed', 'mark_out_for_delivery', 'mark_delivered']

    def mark_confirmed(self, request, queryset):
        for order in queryset.filter(status=Order.Status.PENDING):
            order.update_status(Order.Status.CONFIRMED, changed_by=request.user)
        self.message_user(request, 'Orders marked as Confirmed.')
    mark_confirmed.short_description = 'Mark selected as Confirmed'

    def mark_out_for_delivery(self, request, queryset):
        for order in queryset.filter(status=Order.Status.CONFIRMED):
            order.update_status(Order.Status.OUT_FOR_DELIVERY, changed_by=request.user)
        self.message_user(request, 'Orders marked as Out for Delivery.')
    mark_out_for_delivery.short_description = 'Mark selected as Out for Delivery'

    def mark_delivered(self, request, queryset):
        for order in queryset.filter(status=Order.Status.OUT_FOR_DELIVERY):
            order.update_status(Order.Status.DELIVERED, changed_by=request.user)
        self.message_user(request, 'Orders marked as Delivered.')
    mark_delivered.short_description = 'Mark selected as Delivered'
