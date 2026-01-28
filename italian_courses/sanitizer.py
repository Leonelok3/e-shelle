"""HTML sanitizer to reduce XSS risk when storing HTML in DB.

Recommended:
    pip install bleach
Fallback (if bleach missing): strip to plain text.
"""

from __future__ import annotations
from django.utils.html import strip_tags

def sanitize_html(html: str) -> str:
    html = html or ""
    try:
        import bleach  # type: ignore
    except Exception:
        return strip_tags(html).replace("\n", "<br>")

    allowed_tags = [
        "p", "br", "b", "strong", "i", "em", "u",
        "h2", "h3", "h4",
        "ul", "ol", "li",
        "table", "thead", "tbody", "tr", "th", "td",
        "blockquote",
        "span", "div",
        "a",
        "hr",
    ]
    allowed_attrs = {
        "a": ["href", "title", "target", "rel"],
        "span": ["style"],
        "div": ["style"],
        "table": ["border", "cellpadding", "cellspacing"],
        "th": ["colspan", "rowspan"],
        "td": ["colspan", "rowspan"],
    }
    allowed_protocols = ["http", "https", "mailto"]

    cleaned = bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attrs,
        protocols=allowed_protocols,
        strip=True,
    )
    cleaned = bleach.linkify(cleaned, callbacks=[bleach.callbacks.nofollow, bleach.callbacks.target_blank])
    return cleaned
