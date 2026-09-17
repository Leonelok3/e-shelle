/* auto_cameroun/js/auto.js */

// Utilitaire cookie CSRF
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    for (const cookie of document.cookie.split(';')) {
      const c = cookie.trim();
      if (c.startsWith(name + '=')) {
        cookieValue = decodeURIComponent(c.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

document.addEventListener('DOMContentLoaded', () => {

  // ── Toggle favori ──────────────────────────────────────────
  document.querySelectorAll('.btn-toggle-favori').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.vehiculeId;
      try {
        const resp = await fetch(`/auto/ajax/favori/${id}/`, {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') },
        });
        if (resp.ok) {
          const data = await resp.json();
          if (data.status === 'added') {
            btn.classList.replace('auto-btn--outline', 'auto-btn--favori-actif');
            btn.innerHTML = '<i class="fa-solid fa-heart"></i> Retirer des favoris';
          } else {
            btn.classList.replace('auto-btn--favori-actif', 'auto-btn--outline');
            btn.innerHTML = '<i class="fa-regular fa-heart"></i> Ajouter aux favoris';
          }
        }
      } catch (e) {
        console.error('Erreur favori', e);
      }
    });
  });

  // ── Aperçu photos ──────────────────────────────────────────
  document.querySelectorAll('.auto-photo-controls input[type="file"]').forEach(input => {
    input.addEventListener('change', function () {
      const file = this.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = e => {
        const item = this.closest('.auto-photo-item');
        let img = item.querySelector('.auto-photo-preview');
        if (!img) {
          img = document.createElement('img');
          img.className = 'auto-photo-preview';
          item.insertBefore(img, item.firstChild);
          const dropzone = item.querySelector('.auto-photo-dropzone');
          if (dropzone) dropzone.remove();
        }
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);
    });
  });

  // ── Confirmation suppression ────────────────────────────────
  document.querySelectorAll('.auto-confirm-delete').forEach(form => {
    form.addEventListener('submit', e => {
      if (!confirm('Supprimer définitivement cette annonce ?')) e.preventDefault();
    });
  });

});
