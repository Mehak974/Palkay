from django.contrib import admin
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('product', 'variant', 'quantity', 'added_at')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'total_items', 'subtotal', 'created_at', 'updated_at')
    inlines = [CartItemInline]
    readonly_fields = ('created_at', 'updated_at')
