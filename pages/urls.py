from django.urls import path
from . import views

app_name = 'pages'

urlpatterns = [
    path('',            views.home,     name='home'),
    path('about/',      views.about,    name='about'),
    path('contact/',    views.contact,  name='contact'),
    path('pages/<slug:slug>/', views.cms_page, name='cms_page'),
]
