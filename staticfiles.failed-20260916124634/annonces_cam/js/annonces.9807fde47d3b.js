/**
 * annonces.js — E-Shelle Market
 */

// ── Utilitaire CSRF ─────────────────────────────────────────────
function getCookie(name) {
  let value = null;
  document.cookie.split(";").forEach(c => {
    const [k, v] = c.trim().split("=");
    if (k === name) value = decodeURIComponent(v);
  });
  return value;
}

document.addEventListener("DOMContentLoaded", () => {

  // ── Toggle Favori ────────────────────────────────────────────
  document.querySelectorAll(".btn-toggle-favori").forEach(btn => {
    btn.addEventListener("click", async () => {
      const id   = btn.dataset.annonceId;
      const resp = await fetch(`/annonces/ajax/favori/${id}/`, {
        method: "POST",
        headers: { "X-CSRFToken": getCookie("csrftoken") },
      });
      if (!resp.ok) return;
      const data = await resp.json();
      const icon = btn.querySelector("i");
      if (data.status === "added") {
        btn.classList.add("ann-btn--favori-actif");
        btn.classList.remove("ann-btn--outline");
        if (icon) { icon.classList.remove("fa-regular"); icon.classList.add("fa-solid"); }
        btn.querySelector("span") && (btn.querySelector("span").textContent = "Retirer des favoris");
      } else {
        btn.classList.remove("ann-btn--favori-actif");
        btn.classList.add("ann-btn--outline");
        if (icon) { icon.classList.remove("fa-solid"); icon.classList.add("fa-regular"); }
        btn.querySelector("span") && (btn.querySelector("span").textContent = "Ajouter aux favoris");
      }
    });
  });

  // ── Flash messages auto-dismiss ──────────────────────────────
  document.querySelectorAll(".alert.alert-success, .alert.alert-info").forEach(el => {
    setTimeout(() => {
      el.style.transition = "opacity .5s";
      el.style.opacity    = "0";
      setTimeout(() => el.remove(), 500);
    }, 4000);
  });

  // ── Catégories accordion sidebar ────────────────────────────
  document.querySelectorAll(".ann-cat-parent > .ann-cat-link").forEach(link => {
    const sub = link.nextElementSibling;
    if (!sub) return;
    sub.style.display = "none";
    link.addEventListener("click", e => {
      if (link.getAttribute("href") === "#") e.preventDefault();
      sub.style.display = sub.style.display === "none" ? "block" : "none";
    });
  });

});
