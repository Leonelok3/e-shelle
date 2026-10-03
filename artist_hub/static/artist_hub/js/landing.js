(() => {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!reduced && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });
    document.querySelectorAll('.casting-reveal').forEach(section => {
      if (section.getBoundingClientRect().top > window.innerHeight) {
        section.classList.add('will-reveal');
        observer.observe(section);
      }
    });
  }
  const countdown = document.getElementById('casting-countdown');
  if (!countdown) return;
  const deadline = Date.parse(countdown.dataset.deadline);
  if (!Number.isFinite(deadline)) return;
  let timer;
  const update = () => {
    const remaining = deadline - Date.now();
    if (remaining <= 0) {
      countdown.textContent = 'La période de candidature est terminée.';
      clearInterval(timer);
      return;
    }
    const days = Math.floor(remaining / 86400000);
    const hours = Math.floor((remaining % 86400000) / 3600000);
    countdown.textContent = `${days} jours et ${hours} heures pour présenter votre profil`;
  };
  update();
  if (deadline > Date.now()) timer = setInterval(update, 60000);
})();
