document.addEventListener("DOMContentLoaded", () => {
  const bars = document.querySelectorAll(".cefr-bar-progress");

  bars.forEach(bar => {
    const percent = bar.dataset.percent || 0;
    setTimeout(() => {
      bar.style.width = percent + "%";
    }, 200);
  });
});

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".exam-bar-fill, .radar-fill").forEach(el => {
    const w = el.style.width;
    el.style.width = "0";
    setTimeout(() => (el.style.width = w), 100);
  });
});
