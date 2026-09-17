/**
 * E-Shelle Agro — Devis JS
 * Gestion formulaire de demande de devis + calcul prix dégressif
 */

(function() {
  'use strict';

  // ─── Mise à jour prix selon quantité (prix dégressifs) ───────────────────

  const qteInput   = document.getElementById('id_quantite');
  const prixAffich = document.getElementById('prixEstime');

  if (qteInput && window.PRIX_DEGRESSIF) {
    qteInput.addEventListener('input', function() {
      const qte = parseFloat(this.value) || 0;
      let prixApplique = window.PRIX_BASE;

      if (window.PRIX_DEGRESSIF && window.PRIX_DEGRESSIF.length) {
        const paliers = window.PRIX_DEGRESSIF.slice().sort(function(a, b) {
          return b.qte_min - a.qte_min;
        });
        for (let i = 0; i < paliers.length; i++) {
          if (qte >= paliers[i].qte_min) {
            prixApplique = paliers[i].prix;
            break;
          }
        }
      }

      const total = qte * prixApplique;
      if (prixAffich && total > 0) {
        prixAffich.innerHTML =
          '<strong>' + formatNombre(prixApplique) + ' ' + (window.DEVISE || '') + '</strong> / unité'
          + '<br><span class="text-agro-primary fw-bold">Total estimé : ' + formatNombre(total) + ' ' + (window.DEVISE || '') + '</span>';
        prixAffich.style.display = 'block';
      }
    });
  }

  // ─── Validation formulaire devis ─────────────────────────────────────────

  const devisForm = document.getElementById('devisForm');
  if (devisForm) {
    devisForm.addEventListener('submit', function(e) {
      const msg = document.getElementById('id_message');
      if (msg && msg.value.trim().length < 20) {
        e.preventDefault();
        showError(msg, 'Votre message doit comporter au moins 20 caractères.');
        return false;
      }
      const qte = document.getElementById('id_quantite');
      const moq = parseFloat(qte && qte.dataset.moq) || 0;
      if (qte && parseFloat(qte.value) < moq) {
        e.preventDefault();
        showError(qte, 'La quantité minimum est de ' + moq + ' ' + (qte.dataset.unite || ''));
        return false;
      }
    });
  }

  // ─── Helpers ──────────────────────────────────────────────────────────────

  function formatNombre(n) {
    return parseFloat(n).toLocaleString('fr-FR', { maximumFractionDigits: 2 });
  }

  function showError(input, message) {
    input.classList.add('is-invalid');
    let fb = input.nextElementSibling;
    if (!fb || !fb.classList.contains('invalid-feedback')) {
      fb = document.createElement('div');
      fb.className = 'invalid-feedback';
      input.parentNode.insertBefore(fb, input.nextSibling);
    }
    fb.textContent = message;
    input.addEventListener('input', function() {
      this.classList.remove('is-invalid');
    }, { once: true });
  }

})();
