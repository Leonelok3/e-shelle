document.addEventListener("DOMContentLoaded", () => {
  const textarea = document.querySelector('textarea[name="question"]');
  if (!textarea) return;

  const preset = textarea.dataset.preset;
  if (preset && !textarea.value.trim()) {
    textarea.value = preset;
  }
});
