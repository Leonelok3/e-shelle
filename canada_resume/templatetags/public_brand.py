from django import template
from core.branding import public_text, request_brand

register = template.Library()

@register.filter
def public_brand(value, request):
    return public_text(value, request_brand(request))
