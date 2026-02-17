(function () {
  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(function () {
    const root = document.getElementById("userNav");
    const btn = document.getElementById("userNavBtn");
    const menu = document.getElementById("userNavMenu");
    if (!root || !btn || !menu) return;

    // état initial
    menu.setAttribute("aria-hidden", "true");
    btn.setAttribute("aria-expanded", "false");

    function openMenu() {
      btn.setAttribute("aria-expanded", "true");
      menu.setAttribute("aria-hidden", "false");
      menu.classList.add("is-open");
      root.classList.add("is-open");
    }

    function closeMenu() {
      btn.setAttribute("aria-expanded", "false");
      menu.setAttribute("aria-hidden", "true");
      menu.classList.remove("is-open");
      root.classList.remove("is-open");
    }

    function toggleMenu() {
      const isOpen = btn.getAttribute("aria-expanded") === "true";
      if (isOpen) closeMenu();
      else openMenu();
    }

    // IMPORTANT: empêcher la propagation sinon "document click" referme direct
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      toggleMenu();
    });

    // empêche click dans le menu de fermer
    menu.addEventListener("click", function (e) {
      e.stopPropagation();
    });

    // click dehors => ferme
    document.addEventListener("click", function () {
      closeMenu();
    });

    // mobile: touchstart dehors => ferme
    document.addEventListener(
      "touchstart",
      function () {
        closeMenu();
      },
      { passive: true }
    );

    // ESC => ferme
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeMenu();
    });
  });
})();
