# visaetude/templatetags/visaetude_extras.py
from django import template

register = template.Library()

@register.filter
def percent(value, total):
    try:
        v = float(value); t = float(total)
        return 0 if t == 0 else round((v / t) * 100, 2)
    except Exception:
        return 0

@register.filter
def fcfa(value):
    try:
        return f"{int(value):,} FCFA".replace(",", " ")
    except Exception:
        return f"{value} FCFA"

@register.simple_tag(takes_context=True)
def active(context, name):
    # usage: class="{% active 'visaetude:home' %}"
    try:
        request = context["request"]
        return "active" if request.resolver_match.view_name == name else ""
    except Exception:
        return ""
