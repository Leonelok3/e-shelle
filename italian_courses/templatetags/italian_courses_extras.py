from django import template

register = template.Library()

@register.filter
def get_item(value, key):
    """
    Usage: {{ my_dict|get_item:my_key }}
    Permet d'accéder à un dict avec une clé dynamique dans un template Django.
    """
    if value is None:
        return None
    try:
        return value.get(key)
    except AttributeError:
        try:
            return value[key]
        except Exception:
            return None
