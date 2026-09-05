"""Deterministic source checks: only explicit expiry evidence permits deletion."""
import re
import unicodedata
from datetime import date, datetime
from html import unescape
from urllib.parse import urlparse

import requests


def normalized(value):
    value = unicodedata.normalize("NFKD", unescape(value)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", value).lower().strip()


def parse_deadline(value):
    text = normalized(value or "")
    # Require a complete date: never guess a missing year or ambiguous numeric date.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None
    months = ("janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre")
    for number, month in enumerate(months, 1):
        text = re.sub(rf"\b{month}\b", datetime(2000, number, 1).strftime("%B").lower(), text)
    for fmt in ("%d %B %Y", "%B %d, %Y", "%B %d %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def official_url(url):
    parsed = urlparse(url or "")
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and any(
        host == domain or host.endswith("." + domain)
        for domain in ("jobbank.gc.ca", "guichetemplois.gc.ca")
    ) and not parsed.username and parsed.port in (None, 443)


def check_offer(url):
    """Return (active|expired|unknown, reason, source deadline)."""
    if not official_url(url):
        return "unknown", "URL non officielle", None
    try:
        # Validate each redirect before requesting it.
        for _ in range(6):
            with requests.get(url, timeout=(5, 15), allow_redirects=False,
                              headers={"User-Agent": "Mozilla/5.0 (compatible; EShelleCanadaJobs/1.0)"}) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    from urllib.parse import urljoin
                    url = urljoin(url, response.headers.get("Location", ""))
                    if not official_url(url):
                        return "unknown", "Redirection hors source officielle", None
                    continue
                if response.status_code in (404, 410):
                    return "expired", f"HTTP {response.status_code}", None
                if response.status_code != 200:
                    return "unknown", f"HTTP {response.status_code}", None
                raw = response.text
                text = normalized(re.sub(r"<[^>]+>", " ", re.sub(
                    r"<(script|style)\b.*?</\1>", " ", raw, flags=re.S | re.I)))
                markers = ("job posting no longer advertised", "this job posting is no longer available",
                           "cette offre demploi nest plus disponible", "cette offre d'emploi n'est plus disponible",
                           "offre demploi nest plus annoncee", "offre d'emploi n'est plus annoncee")
                if any(marker in text for marker in markers) or any(
                    marker in url.lower() for marker in ("jobpostingexpired", "job-expired")
                ):
                    return "expired", "Annonce retirée par le site source", None
                match = re.search(r"(?:advertised until|publiee jusqu[' ]?au)\s*(\d{4}-\d{2}-\d{2})", text)
                deadline = parse_deadline(match.group(1)) if match else None
                if deadline or re.search(r'["\']@type["\']\s*:\s*["\']JobPosting["\']', raw):
                    return "active", "Annonce reconnue", deadline
                return "unknown", "Page sans annonce identifiable", None
    except (requests.RequestException, ValueError):
        return "unknown", "Source temporairement inaccessible", None
    return "unknown", "Trop de redirections", None
