/**
 * OCD LIVE — Interactivité client, Countdown & Moteur de réservation
 */
document.addEventListener('DOMContentLoaded', function () {
  // 1. Initialisation du compte à rebours Live
  const countdownEl = document.querySelector('[data-ocd-countdown]');
  if (countdownEl) {
    const targetDateStr = countdownEl.getAttribute('data-ocd-countdown');
    const targetDate = new Date(targetDateStr).getTime();

    function updateCountdown() {
      const now = new Date().getTime();
      const distance = targetDate - now;

      if (distance < 0) {
        countdownEl.innerHTML = '<div class="ocd-badge-live"><span class="pulse-dot"></span> LA SESSION EST EN DIRECT !</div>';
        return;
      }

      const days = Math.floor(distance / (1000 * 60 * 60 * 24));
      const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((distance % (1000 * 60)) / 1000);

      const dEl = countdownEl.querySelector('.timer-days');
      const hEl = countdownEl.querySelector('.timer-hours');
      const mEl = countdownEl.querySelector('.timer-minutes');
      const sEl = countdownEl.querySelector('.timer-seconds');

      if (dEl) dEl.textContent = String(days).padStart(2, '0');
      if (hEl) hEl.textContent = String(hours).padStart(2, '0');
      if (mEl) mEl.textContent = String(minutes).padStart(2, '0');
      if (sEl) sEl.textContent = String(seconds).padStart(2, '0');
    }

    updateCountdown();
    setInterval(updateCountdown, 1000);
  }

  // 2. Filtres par catégorie pour les opportunités
  const filterBtns = document.querySelectorAll('[data-ocd-filter]');
  const opportunityCards = document.querySelectorAll('[data-ocd-category]');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', function () {
      filterBtns.forEach(b => b.classList.remove('active'));
      this.classList.add('active');

      const filterValue = this.getAttribute('data-ocd-filter');

      opportunityCards.forEach(card => {
        if (filterValue === 'all' || card.getAttribute('data-ocd-category') === filterValue) {
          card.style.display = 'flex';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });
});

