/**
 * E-Shelle Agro — Catalogue & Search JS
 */

(function() {
  'use strict';

  // ─── Autocomplete recherche ──────────────────────────────────────────────

  const searchInputs = document.querySelectorAll('[data-agro-search]');
  let searchTimeout;

  searchInputs.forEach(function(input) {
    const resultsEl = document.getElementById('searchResults');
    if (!resultsEl) return;

    input.addEventListener('input', function() {
      const q = this.value.trim();
      clearTimeout(searchTimeout);

      if (q.length < 2) {
        resultsEl.innerHTML = '';
        resultsEl.classList.add('d-none');
        return;
      }

      searchTimeout = setTimeout(function() {
        fetch('/agro/ajax/recherche/?q=' + encodeURIComponent(q))
          .then(function(r) { return r.json(); })
          .then(function(data) {
            renderSearchResults(resultsEl, data, q);
          })
          .catch(function() {
            resultsEl.classList.add('d-none');
          });
      }, 280);
    });

    // Fermer au clic extérieur
    document.addEventListener('click', function(e) {
      if (!input.contains(e.target) && !resultsEl.contains(e.target)) {
        resultsEl.classList.add('d-none');
      }
    });

    // Navigation clavier
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        resultsEl.classList.add('d-none');
      }
    });
  });

  function renderSearchResults(container, data, q) {
    const produits = data.produits || [];
    const acteurs  = data.acteurs  || [];

    if (!produits.length && !acteurs.length) {
      container.innerHTML = '<div class="p-3 text-muted small">Aucun résultat pour « ' + escHtml(q) + ' »</div>';
      container.classList.remove('d-none');
      return;
    }

    let html = '';

    if (produits.length) {
      html += '<div class="agro-search-group px-3 pt-2 pb-1">'
            + '<small class="text-muted text-uppercase fw-semibold" style="font-size:.7rem">Produits</small></div>';
      produits.forEach(function(p) {
        html += '<a href="/agro/produit/' + escAttr(p.slug) + '/" class="agro-search-item d-flex align-items-center gap-2 px-3 py-2">';
        if (p.image) {
          html += '<img src="' + escAttr(p.image) + '" alt="" width="36" height="36" style="object-fit:cover;border-radius:6px">';
        } else {
          html += '<div style="width:36px;height:36px;background:var(--gradient-agro);border-radius:6px;display:flex;align-items:center;justify-content:center;">🌿</div>';
        }
        html += '<div><div class="fw-semibold small">' + escHtml(p.nom) + '</div>'
              + '<div class="text-muted" style="font-size:.75rem">' + escHtml(p.acteur) + ' — ' + escHtml(p.prix) + ' ' + escHtml(p.devise) + '</div></div>';
        html += '</a>';
      });
    }

    if (acteurs.length) {
      html += '<hr class="my-1"><div class="agro-search-group px-3 pt-1 pb-1">'
            + '<small class="text-muted text-uppercase fw-semibold" style="font-size:.7rem">Acteurs</small></div>';
      acteurs.forEach(function(a) {
        html += '<a href="/agro/profil/' + escAttr(a.slug) + '/" class="agro-search-item d-flex align-items-center gap-2 px-3 py-2">'
              + '<div style="width:36px;height:36px;background:var(--gradient-agro);border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:.8rem">'
              + escHtml(a.nom.slice(0, 2).toUpperCase()) + '</div>'
              + '<div><div class="fw-semibold small">' + escHtml(a.nom) + '</div>'
              + '<div class="text-muted" style="font-size:.75rem">' + escHtml(a.type) + ' — ' + escHtml(a.pays) + '</div></div>'
              + '</a>';
      });
    }

    html += '<a href="/agro/recherche/?q=' + encodeURIComponent(q) + '" '
          + 'class="d-block text-center p-2 text-agro-primary fw-semibold small border-top text-decoration-none">'
          + 'Voir tous les résultats pour « ' + escHtml(q) + ' »</a>';

    container.innerHTML = html;
    container.classList.remove('d-none');

    // Style des items
    container.querySelectorAll('.agro-search-item').forEach(function(el) {
      el.style.textDecoration = 'none';
      el.style.color = 'inherit';
      el.style.transition = 'background .15s';
      el.addEventListener('mouseenter', function() { this.style.background = 'var(--agro-light)'; });
      el.addEventListener('mouseleave', function() { this.style.background = ''; });
    });
  }

  // ─── Lazy loading images ──────────────────────────────────────────────────

  if ('IntersectionObserver' in window) {
    const lazyImages = document.querySelectorAll('img[loading="lazy"]');
    const observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          observer.unobserve(entry.target);
        }
      });
    });
    lazyImages.forEach(function(img) { observer.observe(img); });
  }

  // ─── Conversion devises ───────────────────────────────────────────────────

  window.convertirPrix = function(montant, source, cible, callback) {
    fetch('/agro/ajax/convertir-prix/?montant=' + montant + '&source=' + source + '&cible=' + cible)
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (callback && data.montant) callback(data.montant, data.devise);
      })
      .catch(function() {});
  };

  // ─── Helpers ──────────────────────────────────────────────────────────────

  function escHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function escAttr(str) {
    if (!str) return '';
    return String(str).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

})();
