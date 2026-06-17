"""
E-Shelle Resto — Template Tags & Filters
"""
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def fcfa(value):
    """Format a number as FCFA currency: 1500 → '1 500 FCFA'."""
    try:
        int_val = int(value)
        formatted = f"{int_val:,}".replace(",", "\u202f")  # narrow no-break space
        return f"{formatted} FCFA"
    except (TypeError, ValueError):
        return f"{value} FCFA"


@register.filter
def availability_badge(dish):
    """Return an HTML badge for dish availability."""
    colors = {
        "available": "bg-green-100 text-green-800",
        "in_x_minutes": "bg-amber-100 text-amber-800",
        "unavailable": "bg-red-100 text-red-800",
    }
    label = dish.availability_label
    css = colors.get(dish.availability, "bg-gray-100 text-gray-800")
    return mark_safe(
        f'<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {css}">'
        f"{label}</span>"
    )


@register.filter
def status_badge(restaurant):
    """Return an HTML badge for restaurant status."""
    configs = {
        "open": ("Ouvert", "bg-green-500"),
        "closed": ("Fermé", "bg-red-500"),
        "opening_soon": ("Bientôt ouvert", "bg-amber-500"),
    }
    label, bg = configs.get(restaurant.status, ("Inconnu", "bg-gray-400"))
    return mark_safe(
        f'<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold text-white {bg}">'
        f"{label}</span>"
    )


@register.simple_tag
def whatsapp_url(restaurant, dish_name=""):
    """Return WhatsApp wa.me URL for a restaurant, optionally for a specific dish."""
    return restaurant.whatsapp_url(dish_name=dish_name)


@register.inclusion_tag("resto/partials/restaurant_card.html")
def restaurant_card(restaurant):
    """Render a restaurant card."""
    return {"restaurant": restaurant}


@register.inclusion_tag("resto/partials/dish_card.html")
def dish_card(dish):
    """Render a dish card."""
    return {"dish": dish}


@register.filter
def split_time(time_obj):
    """Format time as HHhMM for a clearer French display."""
    if time_obj:
        return time_obj.strftime("%Hh%M")
    return ""
