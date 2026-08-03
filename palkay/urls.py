from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Allow admin URL to be randomised via ADMIN_URL env var
ADMIN_URL = getattr(settings, 'ADMIN_URL', 'admin/')

from django.contrib.sitemaps.views import sitemap
from palkay.sitemaps import ProductSitemap, CategorySitemap, StaticViewSitemap
from django.views.generic import TemplateView
from pages.views import robots_txt

sitemaps = {
    'products': ProductSitemap,
    'categories': CategorySitemap,
    'static': StaticViewSitemap,
}

urlpatterns = [
    path(ADMIN_URL, admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('ads.txt', TemplateView.as_view(template_name='ads.txt', content_type='text/plain'), name='ads_txt'),
    path('9ea100b3d88147d3910c5112eb8b7cd2.txt', TemplateView.as_view(template_name='9ea100b3d88147d3910c5112eb8b7cd2.txt', content_type='text/plain'), name='indexnow'),
    path('', include('pages.urls')),
    path('', include('catalog.urls')),
    path('cart/', include('cart.urls')),
    path('checkout/', include('orders.urls')),
    path('blog/', include('blog.urls')),
    path('admin/analytics/', include('analytics.urls')),
    path('account/', include('users.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

admin.site.site_header = 'Palkay Administration'
admin.site.site_title = 'Palkay Admin'
admin.site.index_title = 'Dashboard'
