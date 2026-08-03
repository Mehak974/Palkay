from django.urls import path
from . import views

app_name = 'support'

urlpatterns = [
    path('', views.ticket_list, name='list'),
    path('new/', views.create_ticket, name='create'),
    path('<int:ticket_id>/', views.ticket_detail, name='detail'),
]
