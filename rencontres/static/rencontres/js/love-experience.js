(() => {
    'use strict';
    document.querySelectorAll('.love-desktop-nav a').forEach(link => {
        if (new URL(link.href).pathname === window.location.pathname) link.setAttribute('aria-current', 'page');
    });
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (reduced.matches) return;
    const panels = document.querySelectorAll('.home-panel, .love-path, .profile-preview, .love-page-intro, .love-landing-hero, .plan-card, .love-international-note, .love-destination');
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('love-reveal');
                    observer.unobserve(entry.target);
                }
            });
        }, {threshold: 0.08});
        panels.forEach(panel => observer.observe(panel));
    }
    const popup = document.getElementById('match-popup');
    if (!popup) return;
    // Celebrate only a real match, when the existing discovery flow opens its popup.
    const observer = new MutationObserver(() => {
        if (reduced.matches || (!popup.classList.contains('show') && !popup.classList.contains('active'))) return;
        const host = popup.querySelector('.popup-content');
        if (!host || host.querySelector('.love-spark')) return;
        for (let i = 0; i < 12; i += 1) {
            const spark = document.createElement('span');
            spark.className = 'love-spark';
            spark.textContent = i % 2 ? '♡' : '✦';
            spark.setAttribute('aria-hidden', 'true');
            const angle = i * Math.PI / 6;
            spark.style.setProperty('--spark-x', `${Math.cos(angle) * 160}px`);
            spark.style.setProperty('--spark-y', `${Math.sin(angle) * 170}px`);
            host.append(spark);
            setTimeout(() => spark.remove(), 1100);
        }
    });
    observer.observe(popup, {attributes: true, attributeFilter: ['class']});
})();
