"""Bounded reads of allowlisted public sources; no guessed publication dates."""
import html
import json
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urldefrag
import requests

HEADERS = {'User-Agent': 'E-Shelle-ContentFetcher/1.1 (+https://e-shelle.com)'}


def allowed(url, domains):
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    return parsed.scheme == 'https' and not parsed.username and not parsed.password and parsed.port in (None, 443) and any(host == d or host.endswith('.' + d) for d in domains)


def fetch(url, domains):
    for _ in range(5):
        if not allowed(url, domains):
            raise ValueError('Source hors liste autorisée')
        response = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=False)
        if response.status_code in (301, 302, 303, 307, 308):
            url = urljoin(url, response.headers['Location'])
            continue
        response.raise_for_status()
        if len(response.content) > 3_000_000:
            raise ValueError('Source trop volumineuse')
        return response.text, url
    raise ValueError('Trop de redirections')


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.title = ''
        self.description = ''
        self.published = ''
        self.links = []
        self.schemas = []
        self._anchor = None
        self._title = False
        self._json = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'a':
            self._anchor = [a.get('href', ''), '']
        if tag == 'title':
            self._title = True
        if tag == 'meta':
            name = (a.get('name') or a.get('property') or '').lower()
            if name in ('description', 'og:description'):
                self.description = a.get('content', '')
            if name in ('article:published_time', 'dcterms.issued', 'datepublished'):
                self.published = a.get('content', '')[:10]
        if tag == 'script' and a.get('type') == 'application/ld+json':
            self._json = ''

    def handle_data(self, data):
        if self._anchor is not None:
            self._anchor[1] += data
        if self._title:
            self.title += data
        if self._json is not None:
            self._json += data

    def handle_endtag(self, tag):
        if tag == 'a' and self._anchor:
            self.links.append(tuple(self._anchor)); self._anchor = None
        if tag == 'title':
            self._title = False
        if tag == 'script' and self._json is not None:
            try:
                value = json.loads(self._json)
                values = value if isinstance(value, list) else [value]
                for item in values:
                    if isinstance(item, dict):
                        self.schemas.append(item)
                        self.schemas.extend(node for node in item.get('@graph', []) if isinstance(node, dict))
            except (ValueError, TypeError):
                pass
            self._json = None


def clean(text):
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]*>', ' ', str(text or '')))).strip()


def catalogue(url, domains, link_filter, limit=12):
    text, final = fetch(url, domains)
    candidates = []
    seen = set()
    for href, title in Page(text).links:
        target = urldefrag(urljoin(final, href))[0]
        if target in seen or not allowed(target, domains) or not link_filter(target):
            continue
        seen.add(target)
        try:
            content, canonical = fetch(target, domains)
            page = Page(content)
            candidates.append({'title': clean(title or page.title), 'url': canonical,
                'host': urlparse(canonical).hostname, 'description': clean(page.description),
                'published': page.published, 'schemas': page.schemas})
        except (requests.RequestException, ValueError):
            continue
        if len(candidates) >= limit:
            break
    return candidates
