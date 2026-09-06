"""Check official sources without treating network failures as expiry."""
import re
from html import unescape
from urllib.parse import urlparse, urljoin
import requests

DOMAINS = ("arbeitsagentur.de", "daad.de", "goethe.de")


def allowed(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and not parsed.username and any(
        host == domain or host.endswith("." + domain) for domain in DOMAINS
    )


def source_expired(url):
    """True only for explicit withdrawal; None when availability is uncertain."""
    try:
        for _ in range(5):
            if not allowed(url):
                return None
            with requests.get(url, timeout=(5, 15), allow_redirects=False,
                              headers={"User-Agent": "Mozilla/5.0 (compatible; EShelle/1.0)"}) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    url = urljoin(url, response.headers.get("Location", ""))
                    continue
                if response.status_code in (404, 410):
                    return True
                if response.status_code != 200:
                    return None
                html = re.sub(r"<(script|style)\b.*?</\1>", " ", response.text, flags=re.I | re.S)
                text = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html))).lower()
                for marker in ("dieses stellenangebot ist nicht mehr verfügbar",
                               "dieses stellenangebot steht nicht mehr zur verfügung",
                               "this job is no longer available", "applications are closed",
                               "bewerbungsfrist ist abgelaufen", "application deadline has passed"):
                    if marker in text:
                        return True
                # A 200 page alone does not prove that the application cycle is open.
                return None
    except (requests.RequestException, ValueError):
        return None
    return None


def check_sources(dry_run=False):
    from .availability import available_offers, available_scholarships
    count = 0
    for qs, field in ((available_offers(), "url_apply"), (available_scholarships(), "url")):
        for item in qs.iterator(chunk_size=100):
            url = getattr(item, field)
            if source_expired(url):
                count += 1
                if not dry_run:
                    filters = {"pk": item.pk, field: url}
                    if hasattr(item, "last_seen"):
                        filters["last_seen"] = item.last_seen
                    qs.model.objects.filter(**filters).update(is_active=False)
    return {"source_withdrawn": count}
