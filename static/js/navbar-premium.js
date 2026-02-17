(function () {
  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(function () {
    const header = document.querySelector(".c-navbar");
    const toggle = document.querySelector(".c-navbar__toggle");
    const nav = document.querySelector(".c-navbar__nav");
    if (!header || !toggle || !nav) return;

    // Accessibilité
    toggle.setAttribute("aria-expanded", "false");

    function openNav() {
      header.classList.add("is-mobile-open");
      toggle.setAttribute("aria-expanded", "true");
    }

    function closeNav() {
      header.classList.remove("is-mobile-open");
      toggle.setAttribute("aria-expanded", "false");
    }

    toggle.addEventListener("click", function (e) {
      e.stopPropagation();
      header.classList.contains("is-mobile-open") ? closeNav() : openNav();
    });

    // click dehors
    document.addEventListener("click", function (e) {
      if (!header.classList.contains("is-mobile-open")) return;
      if (header.contains(e.target)) return;
      closeNav();
    });

    // ESC
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeNav();
    });

    // si on clique un lien nav en mobile => ferme
    nav.addEventListener("click", function (e) {
      const a = e.target.closest("a");
      if (!a) return;
      closeNav();
    });

    // resize => ferme
    window.addEventListener("resize", closeNav);
  });
})();
