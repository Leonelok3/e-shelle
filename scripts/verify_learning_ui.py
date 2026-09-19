"""Render the actual templates with synthetic data; check desktop/mobile layout."""
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edu_cm.settings')

import django
django.setup()
from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import override_settings
from django.utils import timezone
from playwright.sync_api import sync_playwright
from preparation_tests.services.learning_coach import FORMATS, normalize_feedback
from preparation_tests.tests_learning import example_feedback

output = ROOT / 'output' / 'learning-coach-qa'
output.mkdir(parents=True, exist_ok=True)
feedback = normalize_feedback(example_feedback(), 'Je propose une bibliothèque.', 'ee')
request = SimpleNamespace(user=AnonymousUser(), path='/prep/fr/mon-coach/', GET={}, COOKIES={})
context = {
    'csrf_token': 'synthetic-preview-token',
    'request': request, 'exam_code': 'tcf', 'format': FORMATS['tcf'], 'target_level': 'B2',
    'levels': ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'], 'has_personal_focus': True,
    'focus_title': 'Idée → raison → exemple → nuance',
    'focus_technique': 'Développe un argument avec une raison, un exemple précis puis une limite.',
    'next_lessons': [{'skill': skill, 'reason': 'Travailler à mon niveau',
        'lesson': SimpleNamespace(title='Un projet pour mon quartier', level='B2'),
        'url': '/prep/CEFR/ee/lesson/1/'} for skill in ('CO', 'CE', 'EE', 'EO')],
    'history': [{'created_at': timezone.now(), 'score': feedback['score'], 'skill': 'EE',
        'title': 'Un projet pour mon quartier', 'coaching': feedback['coaching'],
        'feedback': feedback['feedback'], 'url': '/prep/CEFR/ee/lesson/1/'}],
}
with override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}):
    html = render_to_string('preparation_tests/learning_center.html', context)
    lesson_request = SimpleNamespace(user=SimpleNamespace(is_authenticated=True), path='/prep/tcf/ee/lesson/1/')
    lesson_context = dict(request=lesson_request, csrf_token='synthetic-preview-token',
        lesson=SimpleNamespace(id=1, title='Un projet pour mon quartier', level='B2', section='ee',
                               content_html='<p>Propose une amélioration et justifie-la avec un exemple.</p>'),
        exercises=[{'obj': SimpleNamespace(id=1, question_text='Proposez une bibliothèque à votre association.',
            instruction='Présentez une proposition, un avantage et une difficulté.'), 'can_audio': True}],
        section='ee', exam_code='tcf', display_exam_code='TCF', is_premium=True,
        progress_completed=0, progress_total=1, progress_percent=0)
    lesson_html = render_to_string('preparation_tests/lesson_session.html', lesson_context)
    chat_html = render_to_string('preparation_tests/ai_coach.html', {
        'request': lesson_request, 'csrf_token': 'synthetic-preview-token', 'is_pro': False,
        'messages_left': 5, 'exam_label': 'TEF', 'target_level': 'B2', 'preset': '',
    })
(output / 'preview.html').write_text(html, encoding='utf-8')

chat_posts = []


def route_request(route):
    url = urlparse(route.request.url)
    if url.netloc != 'learning-preview.local':
        route.abort()
        return
    if url.path == '/prep/fr/mon-coach/':
        route.fulfill(body=html, content_type='text/html')
        return
    if url.path == '/prep/tcf/ee/lesson/1/':
        route.fulfill(body=lesson_html, content_type='text/html')
        return
    if url.path == '/prep/fr/coach/':
        route.fulfill(body=chat_html, content_type='text/html')
        return
    if url.path == '/prep/fr/coach/api/':
        import json
        chat_posts.append(route.request.post_data_json)
        route.fulfill(body=json.dumps({'reply': 'Travaille une raison et un exemple.',
                                      'messages_left': 5 - len(chat_posts)}), content_type='application/json')
        return
    if url.path == '/prep/api/submit-ee/':
        import json
        assert route.request.method == 'POST'
        assert route.request.post_data_json['text'] == 'Je propose une bibliothèque.'
        response = dict(feedback, ok=True, word_count=4, completed_exercises=1, total_exercises=1,
                        percent=100, is_completed=True)
        route.fulfill(body=json.dumps(response), content_type='application/json')
        return
    path = (ROOT / unquote(url.path).lstrip('/')).resolve()
    if path.is_relative_to(ROOT / 'static') and path.is_file():
        import mimetypes
        route.fulfill(path=str(path), content_type=mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
    else:
        route.fulfill(status=404, body='Not in synthetic preview')

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel='msedge', headless=True)
    for width, label in ((1440, 'desktop'), (390, 'mobile')):
        page = browser.new_page(viewport={'width': width, 'height': 1000}, device_scale_factor=1)
        page.route('**/*', route_request)
        page.goto('http://learning-preview.local/prep/fr/mon-coach/', wait_until='networkidle')
        page.locator('.learning-history summary').first.click()
        page.locator('#target-level').select_option('C1')
        assert page.locator('#target-level').input_value() == 'C1'
        assert page.locator('.learning-priority').first.is_visible()
        overflow = page.locator('.learning-shell').evaluate('(node) => node.scrollWidth > node.clientWidth + 1')
        assert not overflow, 'Horizontal overflow at ' + label
        page.evaluate('window.scrollTo(0, 0)')
        page.locator('.learning-shell').screenshot(path=str(output / (label + '.png')))
        print(label, 'layout, history expansion and level selection OK', flush=True)
        page.goto('http://learning-preview.local/prep/tcf/ee/lesson/1/', wait_until='networkidle')
        page.locator('.pt-ee-textarea').fill('Je propose une bibliothèque.')
        page.locator('.pt-submit-ee').click()
        page.locator('.learning-feedback').wait_for(state='visible')
        assert page.locator('.learning-feedback').inner_text().find('Écris deux phrases') >= 0
        assert page.locator('.pt-ee-textarea').input_value() == 'Je propose une bibliothèque.'
        page.locator('.learning-priority summary').click()
        assert page.locator('.learning-priority details').evaluate('(node) => node.open')
        page.locator('.pt-ee-card').screenshot(path=str(output / (label + '-feedback.png')))
        print(label, 'written submission, rubric, exercise and self-check OK', flush=True)
        chat_posts.clear()
        page.goto('http://learning-preview.local/prep/fr/coach/', wait_until='networkidle')
        for index in range(2):
            page.locator('#user-input').fill('Aide-moi à progresser ' + str(index))
            page.locator('#send-btn').click()
            page.wait_for_function('document.getElementById("send-btn").disabled === false')
            assert len(chat_posts[index]['history']) == index * 2
        assert page.locator('#coach-messages-left').inner_text() == '3'
        assert page.locator('#chat-box .ep-msg.user').count() == 2
        print(label, 'two chat turns preserve history and update quota without reloading OK', flush=True)
        page.close()
    browser.close()
