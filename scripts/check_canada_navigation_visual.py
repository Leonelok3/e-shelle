"""Render local templates with synthetic context and inspect desktop/mobile layout."""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edu_cm.settings')

import django
django.setup()

from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, override_settings
from django.urls import resolve, reverse
from playwright.sync_api import sync_playwright

OUTPUT = ROOT / 'output' / 'canada-navigation'
OUTPUT.mkdir(parents=True, exist_ok=True)
PAGES = (
    ('home', 'canada_landing', 'canada/landing.html'),
    ('cv', 'canada_resume:dashboard', 'canada_resume/dashboard.html'),
    ('tcf', 'preparation_tests:tcf_hub', 'preparation_tests/fr_tcf_hub.html'),
    ('onboarding', 'immigration97:onboarding', 'canada_resume/journey/onboarding.html'),
    ('journey', 'immigration97:dashboard', 'canada_resume/journey/dashboard.html'),
)


def main():
    with override_settings(ALLOWED_HOSTS=['testserver'], STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }), sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get('CANADA_TEST_BROWSER') or None,
        )
        for key, route_name, template in PAGES:
            request = RequestFactory().get(reverse(route_name))
            request.resolver_match = resolve(request.path)
            request.user = AnonymousUser()
            from canada_resume.journey_forms import JourneyForm
            from canada_resume.models import ImmigrationJourney
            context = {'request': request, 'user': request.user, 'form': JourneyForm(),
                       'journey': ImmigrationJourney(), 'completed_lessons': 0,
                       'active_days': 0, 'exercise_count': 0, 'checklist_done': 0,
                       'usage': {'remaining': 20, 'limit': 20}}
            html = render_to_string(template, context)
            for width in (1440, 390):
                page = browser.new_page(viewport={'width': width, 'height': 1000})

                def serve(route):
                    url = urlparse(route.request.url)
                    if url.hostname != 'canada.local':
                        route.abort()
                    elif url.path.startswith('/static/'):
                        path = (ROOT / 'static' / unquote(url.path[8:])).resolve()
                        if path.is_relative_to(ROOT / 'static') and path.is_file():
                            route.fulfill(path=str(path))
                        else:
                            route.fulfill(status=404, body='')
                    else:
                        route.fulfill(content_type='text/html', body=html)

                page.route('**/*', serve)
                page.goto('http://canada.local' + request.path)
                page.locator('.canada-navigation').wait_for()
                assert page.locator('.canada-navigation').count() == 1
                page.get_by_text('Tous les modules et assistants IA', exact=True).click()
                assert page.locator('.canada-menu-grid').is_visible()
                assert page.locator('.canada-menu-grid a').count() == 24
                page.get_by_text('Tous les modules et assistants IA', exact=True).click()
                overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth')
                assert not overflow, (key, width, 'horizontal overflow')
                page.screenshot(path=str(OUTPUT / f'{key}-{width}.png'), full_page=False)
                print(key, width, 'navigation and menu OK', flush=True)
                page.close()
        browser.close()


if __name__ == '__main__':
    main()
