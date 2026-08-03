from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.checkout, name='checkout'),
    path('confirmation/<str:order_number>/', views.order_confirmation, name='confirmation'),
    path('my-orders/', views.order_list, name='list'),
    path('my-orders/<str:order_number>/', views.order_detail, name='detail'),
    path('my-orders/<str:order_number>/cancel/', views.cancel_order, name='cancel'),
]
