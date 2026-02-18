/* =========================================================
   IMMIGRATION97 — NAVBAR PREMIUM JS
   - Toggle burger
   - Close on backdrop / outside click
   - Close on Escape
   - Close on link click (mobile)
   - Restore scroll
   - Auto close on resize to desktop
========================================================= */

(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(function () {
    const navbar = document.querySelector("[data-navbar]");
    if (!navbar) return;

    const toggleBtn = navbar.querySelector("[data-nav-toggle]");
    const panel = navbar.querySelector("[data-nav-panel]");
    const backdrop = navbar.querySelector("[data-nav-backdrop]");

    if (!toggleBtn || !panel) return;

    const OPEN_CLASS = "is-open";
    const BODY_OPEN_CLASS = "is-nav-open";

    function isMobile() {
      return window.matchMedia("(max-width: 960px)").matches;
    }

    function setAria(open) {
      toggleBtn.setAttribute("aria-expanded", open ? "true" : "false");
      if (backdrop) backdrop.setAttribute("aria-hidden", open ? "false" : "true");
    }

    function openNav() {
      if (!isMobile()) return;
      navbar.classList.add(OPEN_CLASS);
      document.body.classList.add(BODY_OPEN_CLASS);
      setAria(true);
    }

    function closeNav() {
      navbar.classList.remove(OPEN_CLASS);
      document.body.classList.remove(BODY_OPEN_CLASS);
      setAria(false);
    }

    function toggleNav() {
      const open = navbar.classList.contains(OPEN_CLASS);
      if (open) closeNav();
      else openNav();
    }

    // Toggle button
    toggleBtn.addEventListener("click", function (e) {
      e.preventDefault();
      toggleNav();
    });

    // Backdrop click closes
    if (backdrop) {
      backdrop.addEventListener("click", function () {
        closeNav();
      });
    }

    // Close on ESC
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeNav();
    });

    // Close when clicking a link in panel (mobile UX)
    panel.addEventListener("click", function (e) {
      const target = e.target;
      if (!(target instanceof Element)) return;

      const link = target.closest("a");
      if (!link) return;

      // Only close on mobile to avoid affecting desktop nav behavior
      if (isMobile()) closeNav();
    });

    // Click outside panel closes (only when open)
    document.addEventListener("click", function (e) {
      if (!navbar.classList.contains(OPEN_CLASS)) return;
      const target = e.target;
      if (!(target instanceof Element)) return;

      const insideNavbar = target.closest("[data-navbar]");
      if (!insideNavbar) closeNav();
    });

    // Resize: if we go to desktop, close
    window.addEventListener("resize", function () {
      if (!isMobile()) closeNav();
    }, { passive: true });

    // Initial ARIA
    setAria(false);
  });
})();
