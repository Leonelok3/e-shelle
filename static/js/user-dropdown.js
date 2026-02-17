(function () {
  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(function () {
    const root = document.getElementById("userNav");
    const btn  = document.getElementById("userNavBtn");
    const menu = document.getElementById("userNavMenu");
    if (!root || !btn || !menu) return;

    // état initial
    menu.setAttribute("aria-hidden", "true");
    btn.setAttribute("aria-expanded", "false");

    let isOpen = false;

    function openMenu() {
      isOpen = true;
      root.classList.add("is-open");
      btn.setAttribute("aria-expanded", "true");
      menu.setAttribute("aria-hidden", "false");
    }

    function closeMenu() {
      isOpen = false;
      root.classList.remove("is-open");
      btn.setAttribute("aria-expanded", "false");
      menu.setAttribute("aria-hidden", "true");
    }

    // Click bouton (le plus important)
    btn.addEventListener("click", function (e) {
      // bouton = <button> donc PAS de preventDefault ici
      e.stopPropagation();
      isOpen ? closeMenu() : openMenu();
    });

    // Click dans menu => ne ferme pas
    menu.addEventListener("click", function (e) {
      e.stopPropagation();
    });

    // Click dehors => ferme
    document.addEventListener("click", function (e) {
      if (!isOpen) return;
      if (root.contains(e.target)) return;
      closeMenu();
    });

    // ESC
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && isOpen) closeMenu();
    });

    // Resize => ferme (évite bugs)
    window.addEventListener("resize", function () {
      if (isOpen) closeMenu();
    });
  });
})();
