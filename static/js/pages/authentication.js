document.addEventListener("DOMContentLoaded", () => {

  document.querySelectorAll(".password-wrapper").forEach(wrapper => {
    const input = wrapper.querySelector(".password-input");
    const toggle = wrapper.querySelector(".password-toggle");

    if (!input || !toggle) return;

    const toggleVisibility = (e) => {
      e.preventDefault();
      e.stopPropagation();

      if (input.type === "password") {
        input.type = "text";
        toggle.textContent = "🙈";
      } else {
        input.type = "password";
        toggle.textContent = "👁";
      }

      // 🔒 garde le focus sur l’input
      input.focus();
    };

    // Desktop
    toggle.addEventListener("mousedown", toggleVisibility);

    // Mobile
    toggle.addEventListener("touchstart", toggleVisibility, { passive: false });
  });

});
