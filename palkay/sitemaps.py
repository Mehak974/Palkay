from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from catalog.models import Product, Category
from pages.models import Page


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Category.objects.filter(is_active=True)


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        static_pages = ['pages:home', 'pages:about', 'pages:contact']
        cms_pages = list(Page.objects.filter(is_published=True))
        return static_pages + cms_pages

    def location(self, item):
        if isinstance(item, str):
            return reverse(item)
        return reverse('pages:cms_page', kwargs={'slug': item.slug})

    def lastmod(self, obj):
        if hasattr(obj, 'updated_at'):
            return obj.updated_at
        return None
