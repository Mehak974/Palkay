from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_detail, name='detail'),
    path('add/<uuid:product_id>/', views.cart_add, name='add'),
    path('update/<int:item_id>/', views.cart_update, name='update'),
    path('remove/<int:item_id>/', views.cart_remove, name='remove'),
]
