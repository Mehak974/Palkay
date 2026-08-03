from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('products/', views.product_list, name='product_list'),
    path('products/<slug:slug>/', views.product_detail, name='product'),
    path('<uuid:product_id>/add_review/', views.add_review, name='add_review'),
    path('category/<slug:slug>/', views.category_detail, name='category'),
    path('brand/<slug:slug>/', views.brand_detail, name='brand'),
    path('search/', views.search, name='search'),
    path('wishlist/toggle/<uuid:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
]
