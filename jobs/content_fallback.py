"""Fallback web deterministe pour les collectes Canada lorsque les LLM sont indisponibles."""

import hashlib
import html
import re
import xml.etree.ElementTree as ET
from datetime import date
from ai_engine.services.official_sources import catalogue, fetch, Page, clean
from urllib.parse import parse_qs, unquote, urlencode, urlparse

import requests
from django.utils import timezone


HEADERS = {"User-Agent": "E-Shelle-ContentFetcher/1.0 (+https://e-shelle.com)"}


def _clean(value):
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def search_official(query, domains, limit=8):
    """Retourne des resultats DDG dont le domaine appartient a la liste autorisee."""
    params = urlencode({"q": query, "kl": "ca-en"})
    response = requests.get(
        f"https://html.duckduckgo.com/html/?{params}",
        headers=HEADERS,
        timeout=15,
    )
    response.raise_for_status()
    results = []
    pattern = re.compile(
        r'class="result__a"[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>',
        re.DOTALL,
    )
    for match in pattern.finditer(response.text):
        raw_url = html.unescape(match.group("href"))
        target = parse_qs(urlparse(raw_url).query).get("uddg", [raw_url])[0]
        target = unquote(target)
        host = urlparse(target).netloc.lower().removeprefix("www.")
        if not any(host == domain or host.endswith(f".{domain}") for domain in domains):
            continue
        title = _clean(re.sub(r"<.*?>", "", match.group("title")))
        if not title or not target.startswith("http"):
            continue
        results.append({"title": title, "url": target, "host": host})
        if len(results) >= limit:
            break
    return results


def _ref(prefix, value):
    return f"{prefix}-{hashlib.sha1(value.lower().encode()).hexdigest()[:16]}"


def import_scholarships():
    from jobs.models import CanadaScholarship

    try:
        rows = catalogue('https://www.educanada.ca/scholarships-bourses/non_can/index.aspx?lang=fra',
            ['educanada.ca'], lambda url: '/scholarships-bourses/can/' in url and not urlparse(url).path.endswith('/index.aspx'))
    except (requests.RequestException, ValueError):
        rows = []
    if not rows:
        rows = verified_search('Canada bourses étudiants internationaux site:educanada.ca', ['educanada.ca'])
        rows = [row for row in rows if '/scholarships-bourses/can/' in row['url'] and not urlparse(row['url']).path.endswith('/index.aspx')]
    created = updated = 0
    for row in rows:
        ref = _ref("ca-scholarship", row["url"])
        existing = CanadaScholarship.objects.filter(url_apply=row["url"]).first()
        if existing:
            # Preserve enriched text, dates and editorial decisions already saved.
            existing.save(update_fields=["last_seen"])
            updated += 1
            continue
        _, was_created = CanadaScholarship.objects.update_or_create(
            ref_nr=ref,
            defaults={
                "title": row["title"][:300],
                "provider": row["host"][:200],
                "amount": "Consulter la page officielle",
                "eligibility": "Voir les critères sur la page officielle.",
                "deadline": "Consulter la page officielle",
                "description": "Source officielle détectée automatiquement. Vérifiez les conditions, la date limite et l'éligibilité avant toute candidature.",
                "url_apply": row["url"],
                "is_active": True,
            },
        )
        created += int(was_created)
        updated += int(not was_created)
    return {"created": created, "updated": updated, "found": len(rows)}


def import_visitor_opportunities():
    from jobs.models import CanadaVisitorOpportunity

    rows = verified_search(f'Canada conference registration {timezone.localdate().year} site:canada.ca', ['canada.ca', 'gc.ca', 'destinationcanada.com'])
    # An event must carry machine-readable event facts; a general travel page is not an opportunity.
    rows = [row for row in rows if any(schema.get('@type') == 'Event' for schema in row['schemas'] if isinstance(schema, dict))]
    created = updated = 0
    for row in rows:
        event = next(schema for schema in row['schemas'] if isinstance(schema, dict) and schema.get('@type') == 'Event')
        try:
            end = date.fromisoformat(str(event.get('endDate') or event.get('startDate') or '')[:10])
            start = date.fromisoformat(str(event.get('startDate') or '')[:10])
        except ValueError:
            continue
        location = event.get('location') or {}
        address = location.get('address') or {} if isinstance(location, dict) else {}
        country = address.get('addressCountry', '') if isinstance(address, dict) else ''
        if isinstance(country, dict):
            country = country.get('name', '')
        if end < timezone.localdate() or start > end or str(country).lower() not in ('ca', 'canada'):
            continue
        row['title'] = clean(event.get('name') or row['title'])
        ref = _ref("ca-visitor", row["url"])
        existing = CanadaVisitorOpportunity.objects.filter(url_apply=row["url"]).first()
        if existing:
            # Preserve enriched text, dates and editorial decisions already saved.
            existing.save(update_fields=["last_seen"])
            updated += 1
            continue
        _, was_created = CanadaVisitorOpportunity.objects.update_or_create(
            ref_nr=ref,
            defaults={
                "title": row["title"][:350],
                "organizer": row["host"][:250],
                "event_date": str(event.get("startDate", ""))[:150],
                "location": "Canada",
                "deadline": "Consulter la page officielle",
                "description": "Événement détecté depuis une source officielle. Vérifiez l'inscription et les conditions de visa auprès de l'organisateur.",
                "url_apply": row["url"],
                "is_active": True,
            },
        )
        created += int(was_created)
        updated += int(not was_created)
    return {"created": created, "updated": updated, "found": created + updated}


def import_news():
    from jobs.models import CanadaNews

    rows = official_news()
    if not rows:
        rows = verified_search('Canada immigration dernières actualités site:canada.ca', ['canada.ca', 'quebec.ca'])
    verified = []
    for row in rows:
        try:
            published = date.fromisoformat(row.get('published', ''))
        except (ValueError, TypeError):
            continue
        if timezone.localdate() - timezone.timedelta(days=90) <= published <= timezone.localdate():
            verified.append(row)
    rows = verified
    created = updated = 0
    for row in rows:
        ref = _ref("ca-news", row["url"])
        existing = CanadaNews.objects.filter(url_source=row["url"]).first()
        if existing:
            # Preserve enriched text, dates and editorial decisions already saved.
            existing.save(update_fields=["last_seen"])
            updated += 1
            continue
        _, was_created = CanadaNews.objects.update_or_create(
            ref_nr=ref,
            defaults={
                "title": row["title"][:350],
                "category": "Communiqué",
                "published_date": row.get("published", ""),
                "summary": "Actualité détectée depuis une source officielle. Consultez la page source avant de prendre une décision.",
                "url_source": row["url"],
                "is_active": True,
            },
        )
        created += int(was_created)
        updated += int(not was_created)
    return {"created": created, "updated": updated, "found": len(rows)}


def verified_search(query, domains):
    rows = []
    for item in search_official(query, domains):
        try:
            text, url = fetch(item['url'], domains)
            page = Page(text)
            rows.append({**item, 'url': url, 'description': clean(page.description),
                'published': page.published, 'schemas': page.schemas})
        except (requests.RequestException, ValueError):
            continue
    return rows


def official_news():
    url = 'https://api.io.canada.ca/io-server/gc/news/fr/v2?dept=departmentofcitizenshipandimmigration&format=atom&orderBy=desc&pick=20&sort=publishedDate&type=newsreleases'
    try:
        text, _ = fetch(url, ['canada.ca'])
        root = ET.fromstring(text)
    except (requests.RequestException, ValueError, ET.ParseError):
        return []
    ns = {'a':'http://www.w3.org/2005/Atom'}
    rows = []
    for entry in root.findall('a:entry', ns):
        link = entry.find('a:link', ns)
        if link is None:
            continue
        target = link.get('href', '')
        try:
            content, target = fetch(target, ['canada.ca', 'gc.ca'])
        except (requests.RequestException, ValueError):
            continue
        rows.append({'url':target, 'host':urlparse(target).hostname,
            'title':clean(entry.findtext('a:title', '', ns)),
            'published':entry.findtext('a:published', '', ns)[:10],
            'description':clean(Page(content).description)})
    return rows
