from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import ContactSubmission, Page, Wishlist


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(ModelAdmin):
    list_display = ('name', 'email', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('name', 'email', 'phone', 'subject', 'message', 'created_at')
    
    fieldsets = (
        ('Message Details', {'fields': ('name', 'email', 'phone', 'subject', 'message')}),
        ('Status', {'fields': ('is_read',)}),
        ('Metadata', {'fields': ('created_at',)}),
    )


@admin.register(Page)
class PageAdmin(ModelAdmin):
    list_display = ('title', 'slug', 'is_published', 'updated_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    
    fieldsets = (
        ('Content', {'fields': ('title', 'slug', 'content')}),
        ('Settings', {'fields': ('is_published', 'meta_title', 'meta_description')}),
    )


@admin.register(Wishlist)
class WishlistAdmin(ModelAdmin):
    list_display = ('user', 'product', 'added_at')
    list_filter = ('added_at',)
    raw_id_fields = ('user', 'product')
