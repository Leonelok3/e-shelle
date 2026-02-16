/* =====================================================
   IMMIGRATION97 — Contact FAB (SAFE)
   Ouvre/ferme le panneau, clic dehors, ESC
===================================================== */
document.addEventListener("DOMContentLoaded", () => {
  const fab = document.querySelector(".i97-contactfab");
  if (!fab) return;

  const btn = fab.querySelector(".i97-contactfab__btn");
  const closeBtn = fab.querySelector(".i97-contactfab__close");
  const panel = fab.querySelector(".i97-contactfab__panel");

  if (!btn || !panel) return;

  const setOpen = (open) => {
    fab.classList.toggle("is-open", open);
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    panel.setAttribute("aria-hidden", open ? "false" : "true");
  };

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    setOpen(!fab.classList.contains("is-open"));
  });

  closeBtn?.addEventListener("click", (e) => {
    e.preventDefault();
    setOpen(false);
  });

  // clic dehors
  document.addEventListener(
    "click",
    (e) => {
      if (!fab.classList.contains("is-open")) return;
      if (!fab.contains(e.target)) setOpen(false);
    },
    { passive: true }
  );

  // ESC
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") setOpen(false);
  });
});
