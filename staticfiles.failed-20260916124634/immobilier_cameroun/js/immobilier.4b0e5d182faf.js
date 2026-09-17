/**
 * immobilier.js — E-Shelle Immo
 * AJAX favoris, partage, copier lien, marquer réservé, GLightbox
 */
"use strict";

// ── Utilitaire CSRF ────────────────────────────────────────────
function getCookie(name) {
  const v = document.cookie.match(`(^|;)\\s*${name}\\s*=\\s*([^;]+)`);
  return v ? v.pop() : "";
}

// ── Toggle favori (cards catalogue et détail) ─────────────────
document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".immo-btn-favori, .btn-toggle-favori");
  if (!btn) return;
  e.preventDefault();

  const bienId = btn.dataset.bienId;
  if (!bienId) return;

  try {
    const resp = await fetch(`/immobilier/ajax/toggle-favori/${bienId}/`, {
      method: "POST",
      headers: { "X-CSRFToken": getCookie("csrftoken") },
    });
    if (!resp.ok) {
      if (resp.status === 302 || resp.status === 403) {
        window.location.href = `/accounts/login/?next=${window.location.pathname}`;
      }
      return;
    }
    const data = await resp.json();

    // Mise à jour de l'icône
    const icon = btn.querySelector("i");
    if (data.statut === "ajouté") {
      icon?.classList.replace("fa-regular", "fa-solid");
      btn.classList.add("immo-btn-favori--actif", "immo-btn--favori-actif");
      btn.classList.remove("immo-btn--outline");
      if (btn.classList.contains("btn-toggle-favori")) {
        btn.innerHTML = `<i class="fa-solid fa-heart"></i> Retirer des favoris`;
        btn.classList.add("immo-btn--favori-actif");
      }
    } else {
      icon?.classList.replace("fa-solid", "fa-regular");
      btn.classList.remove("immo-btn-favori--actif", "immo-btn--favori-actif");
      btn.classList.add("immo-btn--outline");
      if (btn.classList.contains("btn-toggle-favori")) {
        btn.innerHTML = `<i class="fa-regular fa-heart"></i> Ajouter aux favoris`;
        btn.classList.remove("immo-btn--favori-actif");
      }
    }

    // Mise à jour compteur si présent dans la page
    const counter = document.querySelector(`[data-favoris-count="${bienId}"]`);
    if (counter) counter.textContent = data.nb_favoris;

  } catch (err) {
    console.error("Erreur toggle favori:", err);
  }
});

// ── Copier le lien (bouton partage) ───────────────────────────
document.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-copy-url]");
  if (!btn) return;

  const url = btn.dataset.copyUrl;
  try {
    // URL absolue si chemin relatif
    const fullUrl = url.startsWith("http") ? url : `${window.location.origin}${url}`;
    await navigator.clipboard.writeText(fullUrl);

    // Feedback visuel
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-check"></i> <span>Copié !</span>';
    btn.style.background = "#2D6A4F";
    setTimeout(() => {
      btn.innerHTML = originalHtml;
      btn.style.background = "";
    }, 2000);
  } catch {
    prompt("Copiez ce lien :", url.startsWith("http") ? url : `${window.location.origin}${url}`);
  }
});

// ── Marquer réservé (AJAX) ─────────────────────────────────────
const btnReserve = document.getElementById("btn-marquer-reserve");
if (btnReserve) {
  btnReserve.addEventListener("click", async () => {
    if (!confirm("Marquer ce bien comme Réservé ?")) return;
    const slug = btnReserve.dataset.slug;
    try {
      const resp = await fetch(`/immobilier/ajax/marquer-reserve/${slug}/`, {
        method: "POST",
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      });
      if (resp.ok) {
        btnReserve.innerHTML = '<i class="fa-solid fa-lock"></i> Réservé';
        btnReserve.disabled = true;
        // Mettre à jour le badge de statut
        const badge = document.querySelector(".immo-badge--publie");
        if (badge) {
          badge.textContent = "🔒 Réservé";
          badge.className = badge.className.replace("immo-badge--publie", "immo-badge--reserve");
        }
      }
    } catch (err) {
      console.error(err);
    }
  });
}

// ── Auto-dismiss alerts ────────────────────────────────────────
document.querySelectorAll(".alert[data-auto-dismiss]").forEach(el => {
  setTimeout(() => el.classList.remove("show"), 4000);
});

// ── Prévisualisation photos (upload) ─────────────────────────
document.querySelectorAll('input[type="file"][accept*="image"]').forEach(input => {
  input.addEventListener("change", () => {
    const file = input.files[0];
    if (!file || !file.type.startsWith("image/")) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      let preview = input.parentElement.querySelector(".immo-photo-preview__img");
      if (!preview) {
        preview = document.createElement("img");
        preview.className = "immo-photo-preview__img";
        input.parentElement.prepend(preview);
      }
      preview.src = e.target.result;
    };
    reader.readAsDataURL(file);
  });
});

// ── Carte Leaflet (si présente) ────────────────────────────────
const mapEl = document.getElementById("immo-map");
if (mapEl && typeof L !== "undefined") {
  const lat   = parseFloat(mapEl.dataset.lat);
  const lng   = parseFloat(mapEl.dataset.lng);
  const titre = mapEl.dataset.titre || "Bien immobilier";
  const map   = L.map("immo-map").setView([lat, lng], 15);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map);
  L.marker([lat, lng])
    .addTo(map)
    .bindPopup(`<strong>${titre}</strong>`)
    .openPopup();
}

// ── Confirmation suppression bien ─────────────────────────────
document.querySelectorAll("form[data-confirm]").forEach(form => {
  form.addEventListener("submit", (e) => {
    if (!confirm(form.dataset.confirm || "Confirmer cette action ?")) {
      e.preventDefault();
    }
  });
});
