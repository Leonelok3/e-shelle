from django.db.models import Avg, Q

from apps.tibo.models import Category, Product


def product_list(query=None, category_slug=None, min_price=None, max_price=None):
    qs = (
        Product.objects.published()
        .select_related("category", "brand", "supplier")
        .prefetch_related("images", "tags")
    )
    if query:
        qs = qs.filter(
            Q(title__icontains=query)
            | Q(short_description__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__name__icontains=query)
            | Q(brand__name__icontains=query)
        ).distinct()
    if category_slug:
        category = Category.objects.filter(slug=category_slug).first()
        if category:
            qs = qs.filter(Q(category=category) | Q(category__parent=category))
    if min_price:
        qs = qs.filter(price__gte=min_price)
    if max_price:
        qs = qs.filter(price__lte=max_price)
    return qs


def product_detail(slug):
    return (
        Product.objects.published()
        .select_related("category", "brand", "supplier", "inventory")
        .prefetch_related("images", "variants", "reviews", "tags")
        .get(slug=slug)
    )


def trending_products(limit=8):
    return (
        Product.objects.published()
        .filter(is_trending=True)
        .select_related("category", "brand")
        .prefetch_related("images")
        .annotate(review_score=Avg("reviews__rating"))
    )[:limit]

