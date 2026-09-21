"""Browser regression: restore, save and preserve writing during failures."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=os.environ.get('CANADA_TEST_BROWSER') or None)
    page = browser.new_page()
    state = {'text': 'Mon brouillon enregistré.', 'fail': False}
    def route(request):
        if '/brouillon/' in request.request.url:
            if request.request.method == 'POST':
                if state['fail']:
                    request.fulfill(status=503, json={'error': 'Unavailable'})
                    return
                state['text'] = request.request.post_data_json['text']
                request.fulfill(json={'saved': True})
            else:
                request.fulfill(json={'exists': True, 'text': state['text']})
        else:
            request.fulfill(body='<input id="csrf-token" value="test" data-authenticated="1" data-draft-url="/brouillon/0/"><div data-exercise-id="12"><textarea class="pt-ee-textarea"></textarea></div>', content_type='text/html')
    page.route('**/*', route)
    page.goto('http://immigration97.local/')
    page.add_script_tag(path=str(ROOT / 'static/js/immigration97-drafts.js'))
    page.wait_for_function("document.querySelector('textarea').value === 'Mon brouillon enregistré.'")
    page.locator('textarea').fill('Ma nouvelle réponse.')
    page.wait_for_function("document.querySelector('.i97-draft-status').textContent.includes('enregistré dans')")
    assert state['text'] == 'Ma nouvelle réponse.'
    state['fail'] = True
    page.locator('textarea').fill('Je conserve ce texte même si le serveur échoue.')
    page.wait_for_function("document.querySelector('.i97-draft-status').textContent.includes('non enregistré')")
    assert page.locator('textarea').input_value() == 'Je conserve ce texte même si le serveur échoue.'
    assert state['text'] == 'Ma nouvelle réponse.'
    browser.close()
    print('Draft restore, save and failure preservation passed.')
