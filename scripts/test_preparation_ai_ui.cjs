// Exercise the real browser script with a small DOM and simulated HTTP responses.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/preparation_tests.js', 'utf8');

async function submit(response, expected) {
  let click;
  const button = {textContent: 'Corriger', disabled: false,
    addEventListener: (_, handler) => { click = handler; }};
  const result = {style: {}, innerHTML: ''};
  const textarea = {value: 'Mon texte de test.', addEventListener() {}};
  const card = {getAttribute: () => '1', querySelector: selector => ({
    '.pt-ee-textarea': textarea, '.pt-submit-ee': button, '.pt-ee-result': result,
  })[selector] || null};
  const token = {value: 'csrf-test', getAttribute: name => ({
    'data-submit-ee-url': '/prep/api/submit-ee/', 'data-authenticated': '1',
  })[name] || ''};
  const document = {
    cookie: '', addEventListener: (_, ready) => ready(),
    getElementById: id => id === 'csrf-token' ? token : null,
    querySelectorAll: selector => selector === '.pt-ee-card' ? [card] : [],
  };
  vm.runInNewContext(source, {document, fetch: () => response instanceof Error
    ? Promise.reject(response) : Promise.resolve(response)});
  click();
  await new Promise(resolve => setImmediate(resolve));
  assert.match(result.innerHTML, expected);
  assert.equal(button.disabled, false);
  assert.equal(button.textContent, 'Corriger');
  assert.equal(textarea.value, 'Mon texte de test.');
}

(async () => {
  await submit({ok: false, status: 500}, /temporairement indisponible/);
  await submit({ok: true, status: 200, redirected: true}, /session a expiré/);
  await submit({ok: false, status: 403}, /Recharge la page/);
  await submit({ok: true, json: () => Promise.reject(new SyntaxError())}, /temporairement indisponible/);
  await submit(new Error('network'), /Connexion impossible/);
  await submit({ok: true, json: () => Promise.resolve({ok: true, score: 82,
    feedback: '<script>unsafe</script>', word_count: 4})}, /&lt;script&gt;unsafe&lt;\/script&gt;/);
  console.log('6 AI submission UI scenarios passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
