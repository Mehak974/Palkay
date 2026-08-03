from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/',           views.login_view,    name='login'),
    path('register/',        views.register_view, name='register'),
    path('logout/',          views.logout_view,   name='logout'),
    path('',                 views.dashboard,     name='dashboard'),
    path('profile/',         views.profile_edit,  name='profile'),
    path('password/',        views.change_password, name='change_password'),
    path('wishlist/',        views.wishlist,       name='wishlist'),
    path('addresses/',       views.address_list,  name='addresses'),
    path('addresses/add/',   views.address_add,   name='address_add'),
    path('addresses/<int:pk>/edit/',   views.address_edit,   name='address_edit'),
    path('addresses/<int:pk>/delete/', views.address_delete, name='address_delete'),
]
