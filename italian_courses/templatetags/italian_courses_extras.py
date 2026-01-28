# italian_courses/templatetags/italian_courses_extras.py
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Usage :
    {{ my_dict|get_item:object.id }}
    """
    if not dictionary:
        return None
    return dictionary.get(key)
