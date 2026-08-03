from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Cart, CartItem


class CartItemInline(TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('product', 'variant', 'quantity', 'added_at')
    can_delete = False


@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ('__str__', 'total_items', 'subtotal', 'created_at', 'updated_at')
    inlines = [CartItemInline]
    readonly_fields = ('created_at', 'updated_at')
