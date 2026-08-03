from django.contrib import admin
from .models import Ticket
from unfold.admin import ModelAdmin

@admin.register(Ticket)
class TicketAdmin(ModelAdmin):
    list_display = ('subject', 'name', 'email', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('subject', 'name', 'email', 'description')
    list_editable = ('status',)
