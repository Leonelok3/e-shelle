(function () {
  'use strict';
  const config = document.getElementById('csrf-token');
  if (!config || config.dataset.authenticated !== '1' || !config.dataset.draftUrl) return;
  document.querySelectorAll('.pt-ee-textarea').forEach(function (textarea) {
    const card = textarea.closest('[data-exercise-id]');
    if (!card) return;
    const url = config.dataset.draftUrl.replace('/0/', '/' + card.dataset.exerciseId + '/');
    const status = document.createElement('span');
    status.className = 'i97-draft-status';
    status.setAttribute('aria-live', 'polite');
    textarea.insertAdjacentElement('afterend', status);
    let edited = false;
    let timer;
    let queue = Promise.resolve();
    fetch(url, {credentials: 'same-origin'}).then(function (response) {
      if (!response.ok) throw new Error('load');
      return response.json();
    }).then(function (data) {
      if (data.exists && !edited) {
        textarea.value = data.text;
        textarea.dispatchEvent(new Event('input', {bubbles: true}));
        status.textContent = 'Votre brouillon a été restauré.';
      }
    }).catch(function () {
      status.textContent = 'Les brouillons enregistrés sont temporairement indisponibles.';
    });
    function save() {
      const text = textarea.value;
      queue = queue.catch(function () {}).then(async function () {
        status.textContent = 'Enregistrement du brouillon…';
        try {
          const response = await fetch(url, {method: 'POST', credentials: 'same-origin',
            headers: {'Content-Type': 'application/json', 'X-CSRFToken': config.value},
            body: JSON.stringify({text: text})});
          if (!response.ok) throw new Error('save');
          status.textContent = 'Brouillon enregistré dans votre compte.';
        } catch (error) {
          status.textContent = 'Brouillon non enregistré. Gardez cette page ouverte ; modifiez le texte pour réessayer.';
        }
      });
    }
    textarea.addEventListener('input', function () {
      edited = true;
      clearTimeout(timer);
      status.textContent = 'Modifications à enregistrer…';
      timer = setTimeout(save, 900);
    });
    textarea.addEventListener('blur', function () { if (edited) { clearTimeout(timer); save(); } });
  });
}());
