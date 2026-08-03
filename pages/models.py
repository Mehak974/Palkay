from django.db import models
from django.conf import settings
from django.utils.text import slugify
from catalog.models import Product


class Wishlist(models.Model):
    """Customer saved products. Unique per user+product pair."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist_items'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'product')]
        ordering = ['-added_at']

    def __str__(self):
        return f'{self.user.email} → {self.product.name}'


class ContactSubmission(models.Model):
    """Capture contact form submissions. No FK to User — standalone."""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True)
    subject = models.CharField(max_length=100, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.subject or "No subject"} ({self.created_at:%Y-%m-%d})'


class Page(models.Model):
    """Editable CMS pages: About, Contact, Privacy Policy, etc."""
    title = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
