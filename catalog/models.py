import uuid
from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.urls import reverse


class Category(models.Model):
    """
    Product categories with optional self-referential parent for subcategories.
    6 root categories defined in Phase 1.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.PROTECT,
        related_name='children'
    )
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    seo_meta_title = models.CharField(max_length=60, blank=True)
    seo_meta_description = models.CharField(max_length=160, blank=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['sort_order', 'name']

    def __str__(self):
        if self.parent:
            return f'{self.parent.name} › {self.name}'
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:category', kwargs={'slug': self.slug})

    @property
    def active_children(self):
        return self.children.filter(is_active=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Brand(models.Model):
    """Partner brand catalog."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='brands/', null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:brand', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    """
    Core product catalog entry.
    Soft-delete via is_active. Price immutable once ordered.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=220)
    description = models.TextField()
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='products'
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='products'
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    compare_at_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text='Original / strike-through price'
    )
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    amazon_link = models.URLField(
        max_length=500, blank=True, null=True,
        help_text="Link to buy this product on Amazon"
    )
    view_count = models.IntegerField(default=0)
    order_count = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    review_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:product', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first()
        if img:
            return img
        return self.images.first()

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0

    @property
    def discount_percent(self):
        if self.compare_at_price and self.compare_at_price > self.price:
            return int((1 - self.price / self.compare_at_price) * 100)
        return None

    def increment_view(self):
        Product.objects.filter(pk=self.pk).update(view_count=models.F('view_count') + 1)


class ProductImage(models.Model):
    """Gallery images per product. One is_primary per product."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=200)
    is_primary = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'sort_order']

    def __str__(self):
        return f'{self.product.name} - Image {self.pk}'

    def save(self, *args, **kwargs):
        if self.is_primary:
            # Unset other primary images for this product
            ProductImage.objects.filter(
                product=self.product, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        if not self.alt_text:
            self.alt_text = self.product.name
        super().save(*args, **kwargs)


class AttributeType(models.Model):
    """E.g. Size, Color, Material"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class AttributeValue(models.Model):
    """E.g. Small, Red, Cotton"""
    attribute_type = models.ForeignKey(AttributeType, on_delete=models.CASCADE, related_name='values')
    value = models.CharField(max_length=100)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'value']
        unique_together = [('attribute_type', 'value')]

    def __str__(self):
        return f'{self.attribute_type.name}: {self.value}'


class ProductVariant(models.Model):
    """
    Product variant (size, color etc) with independent stock and optional price override.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    sku_variant = models.CharField(max_length=50, unique=True, null=True, blank=True)
    price_override = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text='Leave blank to inherit product price'
    )
    stock_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    attribute_values = models.ManyToManyField(AttributeValue, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        attrs = ', '.join(str(av) for av in self.attribute_values.all())
        return f'{self.product.name} [{attrs}]'

    @property
    def effective_price(self):
        return self.price_override if self.price_override else self.product.price

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0

class Review(models.Model):
    """Product reviews from users."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    title = models.CharField(max_length=150)
    content = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.rating} Stars - {self.product.name} by {self.user.email}'

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg, Count

@receiver([post_save, post_delete], sender=Review)
def update_product_rating(sender, instance, **kwargs):
    product = instance.product
    approved_reviews = product.reviews.filter(is_approved=True)
    stats = approved_reviews.aggregate(avg=Avg('rating'), count=Count('id'))
    product.average_rating = stats['avg'] or 0.0
    product.review_count = stats['count']
    product.save(update_fields=['average_rating', 'review_count'])
