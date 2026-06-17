"""
E-Shelle Resto — Context Processors
Injects cities and food categories globally into all resto templates.
"""
from .models import City, FoodCategory, Notification, Restaurant


def resto_globals(request):
    """Inject global resto data into all templates."""
    ctx = {
        "resto_cities": City.objects.filter(is_active=True).order_by("name"),
        "resto_categories": FoodCategory.objects.all().order_by("order", "name"),
    }

    # Unread notification count for logged-in restaurant owners (used in dashboard sidebar)
    if request.user.is_authenticated:
        restaurant = Restaurant.objects.filter(owner=request.user, is_active=True).order_by("name").first()
        if restaurant:
            ctx["unread_notifications_count"] = Notification.objects.filter(
                restaurant=restaurant, is_read=False
            ).count()
        else:
            ctx["unread_notifications_count"] = 0

    return ctx
