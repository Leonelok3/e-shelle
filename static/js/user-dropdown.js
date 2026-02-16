document.addEventListener("DOMContentLoaded", () => {
  const root = document.getElementById("userNav");
  const btn = document.getElementById("userNavBtn");
  const menu = document.getElementById("userNavMenu");

  if (!root || !btn || !menu) return;

  const open = () => {
    btn.setAttribute("aria-expanded", "true");
    menu.setAttribute("aria-hidden", "false");
    root.classList.add("is-open");
  };

  const close = () => {
    btn.setAttribute("aria-expanded", "false");
    menu.setAttribute("aria-hidden", "true");
    root.classList.remove("is-open");
  };

  const toggle = () => {
    const isOpen = btn.getAttribute("aria-expanded") === "true";
    isOpen ? close() : open();
  };

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    toggle();
  });

  // click outside
  document.addEventListener("click", (e) => {
    if (!root.contains(e.target)) close();
  });

  // ESC to close
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") close();
  });

  // close after menu click (optional but premium feeling)
  menu.addEventListener("click", (e) => {
    const link = e.target.closest("a");
    if (link) close();
  });
});
