from catalog.models import Category


def site_context(request):
    """Inject nav categories and site info into every template."""
    nav_categories = Category.objects.filter(
        is_active=True, parent__isnull=True
    ).order_by('sort_order')[:6]
    return {
        'nav_categories': nav_categories,
        'site_name': 'Palkay',
        'site_tagline': 'Good taste shouldn\'t cost more.',
    }
