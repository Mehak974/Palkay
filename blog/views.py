from django.shortcuts import render, get_object_or_404
from .models import Post, PostCategory

def post_list(request, category_slug=None):
    category = None
    posts = Post.objects.filter(is_published=True).select_related('author', 'category')
    categories = PostCategory.objects.all()

    if category_slug:
        category = get_object_or_404(PostCategory, slug=category_slug)
        posts = posts.filter(category=category)

    return render(request, 'blog/post_list.html', {
        'category': category,
        'posts': posts,
        'categories': categories,
    })

def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, is_published=True)
    return render(request, 'blog/post_detail.html', {'post': post})
