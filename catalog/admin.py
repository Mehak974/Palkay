from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Brand, Product, ProductImage, ProductVariant, AttributeType, AttributeValue, Review
from unfold.admin import ModelAdmin, TabularInline

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'parent', 'sort_order', 'is_active')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('sort_order', 'name')


@admin.register(Brand)
class BrandAdmin(ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'sort_order')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" height="60"/>', obj.image.url)
        return '—'
    image_preview.short_description = 'Preview'


class ProductVariantInline(TabularInline):
    model = ProductVariant
    extra = 0
    fields = ('sku_variant', 'price_override', 'stock_quantity', 'attribute_values')
    filter_horizontal = ('attribute_values',)


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ('name', 'sku', 'category', 'brand', 'price', 'stock_quantity', 'is_active', 'is_featured', 'order_count')
    list_display_links = ('name', 'sku')
    list_filter = ('is_active', 'is_featured', 'category', 'brand')
    search_fields = ('name', 'sku', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('id', 'view_count', 'order_count', 'created_at', 'updated_at')
    # list_editable = ('is_active', 'is_featured', 'stock_quantity')
    inlines = [ProductImageInline, ProductVariantInline]
    fieldsets = (
        ('Core', {'fields': ('id', 'sku', 'name', 'slug', 'description', 'amazon_link')}),
        ('Classification', {'fields': ('category', 'brand')}),
        ('Pricing & Stock', {'fields': ('price', 'compare_at_price', 'stock_quantity')}),
        ('Visibility', {'fields': ('is_active', 'is_featured')}),
        ('Analytics', {'fields': ('view_count', 'order_count', 'created_at', 'updated_at')}),
    )



@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ('product', 'user', 'rating', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating')
    search_fields = ('product__name', 'user__email', 'title')

@admin.register(AttributeType)
class AttributeTypeAdmin(ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(AttributeValue)
class AttributeValueAdmin(ModelAdmin):
    list_display = ('attribute_type', 'value', 'sort_order')
    list_filter = ('attribute_type',)
