from django.contrib import admin
from django.db import models
from .models import Post, PostCategory
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import WysiwygWidget

@admin.register(PostCategory)
class PostCategoryAdmin(ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = ('title', 'category', 'author', 'is_published', 'created_at')
    list_filter = ('is_published', 'category')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        }
    }
