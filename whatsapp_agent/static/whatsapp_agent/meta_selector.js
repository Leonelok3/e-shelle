(() => {
  document.querySelectorAll('[data-meta-selector]').forEach(root => {
    const select = root.querySelector('select');
    const status = root.querySelector('[data-meta-status]');
    const preview = root.querySelector('[data-meta-preview]');
    const variables = root.querySelector('[data-meta-variables]');
    const params = root.querySelector('[data-meta-params]');
    const savedNode = document.getElementById('saved-meta-params');
    let saved = savedNode ? JSON.parse(savedNode.textContent) : [];
    let templates = [];
    let selected = root.dataset.selected;
    if (selected) {
      select.add(new Option(selected.replace('|', ' (' ) + ') — enregistre', selected, true, true));
      params.value = JSON.stringify(saved);
    }
    function render() {
      variables.replaceChildren();
      const template = templates.find(t => t.key === select.value);
      preview.textContent = template ? template.body : '';
      const values = [];
      if (template) {
        for (let i = 0; i < template.parameter_count; i++) {
          const label = document.createElement('label');
          label.textContent = `Variable ${i + 1}`;
          const input = document.createElement('input');
          input.className = 'wa-input';
          input.maxLength = 1024;
          input.required = true;
          input.value = saved[i] || (i === 0 ? '{{prenom}}' : '');
          values.push(input);
          variables.append(label, input);
          input.addEventListener('input', sync);
        }
      }
      function sync() { params.value = JSON.stringify(values.map(input => input.value)); }
      sync();
    }
    select.addEventListener('change', () => { saved = []; selected = select.value; render(); });
    async function load() {
      status.textContent = 'Chargement des modeles approuves…';
      try {
        const response = await fetch(root.dataset.url, {headers: {Accept: 'application/json'}});
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Impossible de charger les modeles.');
        templates = data.templates;
        select.replaceChildren(new Option('Message texte de la campagne', ''));
        for (const t of templates) {
          const option = new Option(`${t.name} (${t.language}) — ${t.category}${t.supported ? '' : ' — non pris en charge'}`, t.key);
          option.disabled = !t.supported;
          select.add(option);
        }
        if (selected && !templates.some(t => t.key === selected && t.supported)) {
          select.add(new Option(selected + ' — indisponible', selected));
          select.value = selected;
          status.textContent = 'Le modele enregistre est indisponible. Choisis un autre modele avant l’envoi.';
        } else {
          select.value = selected || '';
          status.textContent = `${templates.length} modele(s) approuve(s). La langue est selectionnee automatiquement.`;
          render();
        }
      } catch (error) {
        status.textContent = error.message;
      }
    }
    root.querySelector('[data-meta-refresh]').addEventListener('click', load);
    load();
  });
})();
