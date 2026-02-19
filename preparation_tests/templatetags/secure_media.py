# preparation_tests/templatetags/secure_media.py
from __future__ import annotations

from django import template
from django.conf import settings

register = template.Library()


def _map_media_to_protected(url: str) -> str:
    """
    Convertit une URL publique /media/... en URL sécurisée /protected-media/...
    """
    media_url = getattr(settings, "MEDIA_URL", "/media/")
    protected_url = getattr(settings, "PROTECTED_MEDIA_URL", "/protected-media/")

    if url.startswith(media_url):
        rest = url[len(media_url):].lstrip("/")
        return protected_url.rstrip("/") + "/" + rest

    return url


@register.simple_tag
def secure_asset_url(asset) -> str:
    """
    Usage template:
        {% load secure_media %}
        <source src="{% secure_asset_url exercise.audio %}" type="audio/mpeg">

    - Prend asset.secure_url si dispo
    - Sinon convertit asset.file.url (/media/...) -> (/protected-media/...)
    """
    if not asset:
        return ""

    secure_url = getattr(asset, "secure_url", None)
    if secure_url:
        return secure_url

    f = getattr(asset, "file", None)
    if f and getattr(f, "url", None):
        return _map_media_to_protected(f.url)

    return ""


@register.simple_tag
def secure_media_url(url: str | None) -> str:
    """
    Usage template:
        {% secure_media_url some_url %}
    """
    if not url:
        return ""
    return _map_media_to_protected(url)
