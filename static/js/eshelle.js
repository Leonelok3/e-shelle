/**
 * E-SHELLE — JavaScript Utilitaires v2026
 * Plateforme SaaS Africaine — Made in Cameroon 🇨🇲
 */

'use strict';

/* ========================================================
   1. PARTICULES CANVAS
   ======================================================== */
function initParticles(canvasId = 'particles-canvas') {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let particles = [];
  const PARTICLE_COUNT = 60;
  const GREEN = '46,125,50';

  function resize() {
    canvas.width  = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
  }

  function createParticle() {
    return {
      x:     Math.random() * canvas.width,
      y:     Math.random() * canvas.height,
      vx:    (Math.random() - 0.5) * 0.6,
      vy:    (Math.random() - 0.5) * 0.6,
      radius: Math.random() * 2 + 0.5,
      alpha:  Math.random() * 0.5 + 0.1,
    };
  }

  function init() {
    resize();
    particles = Array.from({ length: PARTICLE_COUNT }, createParticle);
  }

  function drawLine(a, b) {
    const dist = Math.hypot(a.x - b.x, a.y - b.y);
    if (dist > 140) return;
    const alpha = (1 - dist / 140) * 0.15;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.strokeStyle = `rgba(${GREEN},${alpha})`;
    ctx.lineWidth = 0.8;
    ctx.stroke();
  }

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    particles.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0 || p.x > canvas.width)  p.vx *= -1;
      if (p.y < 0 || p.y > canvas.height) p.vy *= -1;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${GREEN},${p.alpha})`;
      ctx.fill();
    });

    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        drawLine(particles[i], particles[j]);
      }
    }

    requestAnimationFrame(animate);
  }

  init();
  animate();
  window.addEventListener('resize', init);
}

/* ========================================================
   2. COMPTEURS ANIMÉS
   ======================================================== */
function initCounters() {
  const counters = document.querySelectorAll('[data-counter]');
  if (!counters.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting || entry.target.dataset.done) return;
      entry.target.dataset.done = '1';

      const target  = parseInt(entry.target.dataset.counter, 10);
      const suffix  = entry.target.dataset.suffix || '';
      const duration = 1800;
      const start    = performance.now();

      function tick(now) {
        const elapsed  = now - start;
        const progress = Math.min(elapsed / duration, 1);
        // Easing easeOutCubic
        const eased   = 1 - Math.pow(1 - progress, 3);
        const value   = Math.round(eased * target);
        entry.target.textContent = value.toLocaleString('fr-FR') + suffix;

        if (progress < 1) requestAnimationFrame(tick);
        else {
          entry.target.textContent = target.toLocaleString('fr-FR') + suffix;
          entry.target.classList.add('counter-done');
        }
      }
      requestAnimationFrame(tick);
    });
  }, { threshold: 0.5 });

  counters.forEach(el => observer.observe(el));
}

/* ========================================================
   3. NAVBAR AU SCROLL
   ======================================================== */
function initScrollNav() {
  const navbar = document.getElementById('main-navbar');
  if (!navbar) return;

  let lastScroll = 0;

  window.addEventListener('scroll', () => {
    const scrollY = window.scrollY;

    if (scrollY > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }

    // Masquer la navbar en scrollant vers le bas, réafficher en remontant
    if (scrollY > lastScroll && scrollY > 300) {
      navbar.style.transform = 'translateY(-100%)';
    } else {
      navbar.style.transform = 'translateY(0)';
    }
    lastScroll = scrollY;
  }, { passive: true });
}

/* ========================================================
   4. ANIMATIONS AU SCROLL (AOS-like)
   ======================================================== */
function initScrollAnimations() {
  const els = document.querySelectorAll('.aos-hidden');
  if (!els.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('aos-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  els.forEach(el => observer.observe(el));
}

/* ========================================================
   5. MENU BURGER MOBILE
   ======================================================== */
function initMobileMenu() {
  const burger    = document.getElementById('burger-btn');
  const mobileNav = document.getElementById('navbar-mobile');
  if (!burger || !mobileNav) return;

  function closeMenu() {
    burger.classList.remove('open');
    mobileNav.classList.remove('open');
    document.body.classList.remove('menu-open');
    burger.setAttribute('aria-expanded', 'false');
  }

  burger.addEventListener('click', () => {
    const isOpen = mobileNav.classList.toggle('open');
    burger.classList.toggle('open', isOpen);
    document.body.classList.toggle('menu-open', isOpen);
    burger.setAttribute('aria-expanded', String(isOpen));
  });

  // Fermer au clic sur un lien
  mobileNav.querySelectorAll('.nav-link, a').forEach(link => {
    link.addEventListener('click', closeMenu);
  });

  // Fermer avec Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeMenu();
  });

  // Fermer si on repasse en desktop
  window.addEventListener('resize', () => {
    if (window.innerWidth > 768) closeMenu();
  });
}

/* ========================================================
   5b. NAV DROPDOWNS (desktop) — hover + click/touch
   ======================================================== */
function initNavDropdowns() {
  const items = document.querySelectorAll('.nav-dropdown');

  function openMenu(li) {
    const menu = li.querySelector('.nav-dropdown__menu');
    const btn  = li.querySelector('.nav-dropdown__toggle');
    if (!menu) return;
    // Fermer les autres
    items.forEach(other => {
      if (other !== li) {
        other.querySelector('.nav-dropdown__menu')?.classList.remove('dd-open');
        other.querySelector('.nav-dropdown__toggle')?.setAttribute('aria-expanded', 'false');
      }
    });
    menu.classList.add('dd-open');
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }

  function closeMenu(li) {
    const menu = li.querySelector('.nav-dropdown__menu');
    const btn  = li.querySelector('.nav-dropdown__toggle');
    menu?.classList.remove('dd-open');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  }

  items.forEach(li => {
    let closeTimer;
    // Hover desktop — délai 200ms pour éviter fermeture dans le gap bouton/menu
    li.addEventListener('mouseenter', () => { clearTimeout(closeTimer); openMenu(li); });
    li.addEventListener('mouseleave', () => { closeTimer = setTimeout(() => closeMenu(li), 200); });

    // Click/touch (mobile + accessibilité)
    const btn = li.querySelector('.nav-dropdown__toggle');
    if (btn) {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = li.querySelector('.nav-dropdown__menu')?.classList.contains('dd-open');
        isOpen ? closeMenu(li) : openMenu(li);
      });
    }
  });

  // Fermer au clic ailleurs
  document.addEventListener('click', () => {
    items.forEach(li => closeMenu(li));
  });

  // Fermer avec Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') items.forEach(li => closeMenu(li));
  });
}

/* ========================================================
   6. SLIDER TÉMOIGNAGES
   ======================================================== */
function initTestimonialSlider() {
  const track  = document.getElementById('testimonial-track');
  const dots   = document.querySelectorAll('.slider-dot');
  if (!track || !dots.length) return;

  const slides = track.querySelectorAll('.testimonial-card');
  let current  = 0;
  let timer;

  function goTo(index) {
    current = (index + slides.length) % slides.length;
    const width = track.parentElement ? track.parentElement.clientWidth : track.clientWidth;
    track.style.transform = `translateX(-${current * width}px)`;
    dots.forEach((d, i) => d.classList.toggle('active', i === current));
  }

  function next() { goTo(current + 1); }

  function startTimer() {
    clearInterval(timer);
    timer = setInterval(next, 4000);
  }

  dots.forEach((dot, i) => {
    dot.addEventListener('click', () => { goTo(i); startTimer(); });
  });

  // Swipe touch
  let touchX = 0;
  track.addEventListener('touchstart', e => { touchX = e.touches[0].clientX; }, { passive: true });
  track.addEventListener('touchend',   e => {
    const diff = touchX - e.changedTouches[0].clientX;
    if (Math.abs(diff) > 50) { diff > 0 ? goTo(current + 1) : goTo(current - 1); startTimer(); }
  });

  window.addEventListener('resize', () => goTo(current));

  goTo(0);
  startTimer();
}

/* ========================================================
   7. TOASTS
   ======================================================== */
const Toasts = (() => {
  let container;

  function getContainer() {
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  const ICONS = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };

  function show({ type = 'info', title = '', message = '', duration = 4000 }) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${ICONS[type] || '💬'}</span>
      <div class="toast-content">
        ${title ? `<div class="toast-title">${title}</div>` : ''}
        ${message ? `<div class="toast-msg">${message}</div>` : ''}
      </div>
      <button class="toast-close" aria-label="Fermer">✕</button>
    `;

    const close = toast.querySelector('.toast-close');
    const dismiss = () => {
      toast.style.opacity    = '0';
      toast.style.transform  = 'translateX(40px)';
      toast.style.transition = 'all 0.25s ease';
      setTimeout(() => toast.remove(), 260);
    };
    close.addEventListener('click', dismiss);
    if (duration > 0) setTimeout(dismiss, duration);

    getContainer().appendChild(toast);
    return toast;
  }

  return {
    success: (msg, title = 'Succès')    => show({ type: 'success', title, message: msg }),
    error:   (msg, title = 'Erreur')    => show({ type: 'error',   title, message: msg }),
    info:    (msg, title = 'Info')      => show({ type: 'info',    title, message: msg }),
    warning: (msg, title = 'Attention') => show({ type: 'warning', title, message: msg }),
    show,
  };
})();

/* ========================================================
   8. MODALS
   ======================================================== */
const Modal = (() => {
  function open(id) {
    const overlay = document.getElementById(id);
    if (!overlay) return;
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';

    overlay.addEventListener('click', e => {
      if (e.target === overlay) Modal.close(id);
    }, { once: true });
  }

  function close(id) {
    const overlay = document.getElementById(id);
    if (!overlay) return;
    overlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  // Initialise tous les boutons data-modal-open / data-modal-close
  function init() {
    document.querySelectorAll('[data-modal-open]').forEach(btn => {
      btn.addEventListener('click', () => open(btn.dataset.modalOpen));
    });
    document.querySelectorAll('[data-modal-close]').forEach(btn => {
      btn.addEventListener('click', () => close(btn.dataset.modalClose));
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.open').forEach(o => {
          close(o.id);
        });
      }
    });
  }

  return { open, close, init };
})();

/* ========================================================
   9. PANIER SLIDE-IN
   ======================================================== */
function initCart() {
  const panel    = document.getElementById('cart-panel');
  const backdrop = document.getElementById('cart-backdrop');
  const openBtns  = document.querySelectorAll('[data-open-cart]');
  const closeBtns = document.querySelectorAll('[data-close-cart]');
  if (!panel) return;

  const open  = () => { panel.classList.add('open'); if (backdrop) backdrop.classList.add('open'); document.body.style.overflow = 'hidden'; };
  const close = () => { panel.classList.remove('open'); if (backdrop) backdrop.classList.remove('open'); document.body.style.overflow = ''; };

  openBtns.forEach(b  => b.addEventListener('click', open));
  closeBtns.forEach(b => b.addEventListener('click', close));
  if (backdrop) backdrop.addEventListener('click', close);
}

/* ========================================================
   10. SIDEBAR MOBILE
   ======================================================== */
function initSidebar() {
  const sidebar    = document.getElementById('app-sidebar');
  const toggleBtns = document.querySelectorAll('[data-toggle-sidebar]');
  if (!sidebar) return;

  toggleBtns.forEach(btn => {
    btn.addEventListener('click', () => sidebar.classList.toggle('open'));
  });

  // Fermer en cliquant à l'extérieur
  document.addEventListener('click', e => {
    if (window.innerWidth < 1024 && sidebar.classList.contains('open')
        && !sidebar.contains(e.target) && !e.target.closest('[data-toggle-sidebar]')) {
      sidebar.classList.remove('open');
    }
  });
}

/* ========================================================
   11. TABS
   ======================================================== */
function initTabs() {
  document.querySelectorAll('[data-tabs]').forEach(tabGroup => {
    const triggers = tabGroup.querySelectorAll('[data-tab]');
    const panels   = tabGroup.querySelectorAll('[data-tab-panel]');

    triggers.forEach(trigger => {
      trigger.addEventListener('click', () => {
        const target = trigger.dataset.tab;
        triggers.forEach(t => t.classList.toggle('active', t.dataset.tab === target));
        panels.forEach(p => p.classList.toggle('hidden', p.dataset.tabPanel !== target));
      });
    });

    // Activer le premier par défaut
    if (triggers.length) triggers[0].click();
  });
}

/* ========================================================
   12. FILTRES (tags actifs)
   ======================================================== */
function initFilters() {
  document.querySelectorAll('[data-filter-group]').forEach(group => {
    group.querySelectorAll('[data-filter]').forEach(btn => {
      btn.addEventListener('click', () => {
        group.querySelectorAll('[data-filter]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const filter  = btn.dataset.filter;
        const target  = document.getElementById(group.dataset.filterGroup);
        if (!target) return;

        target.querySelectorAll('[data-category]').forEach(item => {
          const show = filter === 'all' || item.dataset.category === filter;
          item.style.display = show ? '' : 'none';
          item.style.opacity = show ? '1' : '0';
        });
      });
    });
  });
}

/* ========================================================
   13. STREAMING IA
   ======================================================== */
async function aiStream(endpoint, payload, outputEl, { onDone, onError } = {}) {
  if (!outputEl) return;
  outputEl.textContent = '';
  outputEl.classList.add('streaming');

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrf(),
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      outputEl.textContent += decoder.decode(value, { stream: true });
      // Auto-scroll
      outputEl.scrollTop = outputEl.scrollHeight;
    }

    outputEl.classList.remove('streaming');
    if (onDone) onDone(outputEl.textContent);
  } catch (err) {
    outputEl.classList.remove('streaming');
    outputEl.textContent = '⚠️ Erreur de génération. Réessaie.';
    if (onError) onError(err);
    console.error('[aiStream]', err);
  }
}

/* ========================================================
   14. UTILITAIRES
   ======================================================== */

/** Récupère le token CSRF depuis les cookies */
function getCsrf() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : '';
}

/** Debounce */
function debounce(fn, delay = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
}

/** Formater prix FCFA */
function formatFcfa(amount) {
  return new Intl.NumberFormat('fr-FR').format(amount) + ' FCFA';
}

/** Copier dans le presse-papier */
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    Toasts.success('Copié dans le presse-papier !', '');
  } catch {
    Toasts.error('Impossible de copier.', '');
  }
}

/** Animer l'ajout au panier (+1) */
function animateAddToCart(btn) {
  const original = btn.innerHTML;
  btn.innerHTML = '✓';
  btn.style.background = 'var(--primary)';
  btn.style.color = '#fff';
  setTimeout(() => {
    btn.innerHTML = original;
    btn.style.background = '';
    btn.style.color = '';
  }, 1200);
}

/** AJAX fetch wrapper (GET / POST) */
async function ajax(url, options = {}) {
  const defaults = {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrf(),
      'X-Requested-With': 'XMLHttpRequest',
    },
  };
  const config = { ...defaults, ...options };
  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }
  const res = await fetch(url, config);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/* ========================================================
   15. BARRE DE PROGRESSION LECTEUR DE COURS
   ======================================================== */
function initCourseProgress() {
  const fills = document.querySelectorAll('.progress-fill[data-progress]');
  fills.forEach(fill => {
    const val = parseFloat(fill.dataset.progress) || 0;
    setTimeout(() => { fill.style.width = Math.min(val, 100) + '%'; }, 300);
  });
}

/* ========================================================
   16. SEARCH OVERLAY
   ======================================================== */
function initSearchOverlay() {
  const openBtn  = document.getElementById('search-btn');
  const overlay  = document.getElementById('search-overlay');
  const input    = document.getElementById('search-input');
  const results  = document.getElementById('search-results');
  if (!openBtn || !overlay) return;

  const open  = () => { overlay.classList.add('open'); setTimeout(() => input?.focus(), 100); };
  const close = () => overlay.classList.remove('open');

  openBtn.addEventListener('click', open);
  overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') close();
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); open(); }
  });

  if (input && results) {
    input.addEventListener('input', debounce(async () => {
      const q = input.value.trim();
      if (q.length < 2) { results.innerHTML = ''; return; }
      try {
        const data = await ajax(`/api/v1/search/?q=${encodeURIComponent(q)}`);
        renderSearchResults(data, results);
      } catch {
        results.innerHTML = '<p class="text-muted" style="padding:1rem">Erreur de recherche.</p>';
      }
    }, 350));
  }
}

function renderSearchResults(data, container) {
  if (!data.results?.length) {
    const unmet = data.unmet_search || {};
    container.innerHTML = `
      <div style="padding:1rem">
        <strong style="display:block;color:var(--text-primary);margin-bottom:.35rem">Aucun resultat parfait dans E-Shelle.</strong>
        <p class="text-muted" style="margin:0 0 .8rem">${unmet.message || 'E-Shelle peut chercher pour vous.'}</p>
        <div style="display:flex;gap:.5rem;flex-wrap:wrap">
          ${unmet.capture_url ? `<a class="btn btn-primary btn-sm" href="${unmet.capture_url}">Demander au reseau</a>` : ''}
          ${unmet.chat_url ? `<a class="btn btn-outline btn-sm" href="${unmet.chat_url}">Chercher avec IA</a>` : ''}
          ${unmet.google_url ? `<a class="btn btn-outline btn-sm" target="_blank" rel="noopener" href="${unmet.google_url}">Google</a>` : ''}
          ${unmet.facebook_url ? `<a class="btn btn-outline btn-sm" target="_blank" rel="noopener" href="${unmet.facebook_url}">Facebook</a>` : ''}
        </div>
      </div>
    `;
    return;
  }
  container.innerHTML = data.results.map(r => `
    <a href="${r.url}" class="search-result-item">
      <span class="search-result-type badge badge-gray">${r.type}</span>
      <span class="search-result-title">${r.title}</span>
    </a>
  `).join('');
}

/* ========================================================
   17. CONFETTIS (fin de leçon)
   ======================================================== */
function launchConfetti() {
  const colors = ['#2E7D32','#4CAF50','#F57C00','#FFB74D','#FAFAFA'];
  const container = document.createElement('div');
  container.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:9999;overflow:hidden';
  document.body.appendChild(container);

  for (let i = 0; i < 80; i++) {
    const el = document.createElement('div');
    const size = Math.random() * 10 + 6;
    el.style.cssText = `
      position:absolute;
      width:${size}px;height:${size}px;
      background:${colors[Math.floor(Math.random()*colors.length)]};
      border-radius:${Math.random() > 0.5 ? '50%' : '2px'};
      left:${Math.random()*100}%;
      top:-20px;
      opacity:${Math.random() * 0.8 + 0.2};
      animation:confetti-fall ${Math.random() * 2 + 1.5}s ease-in forwards;
      animation-delay:${Math.random() * 0.8}s;
    `;
    container.appendChild(el);
  }

  // Injecter keyframes si absent
  if (!document.getElementById('confetti-style')) {
    const style = document.createElement('style');
    style.id = 'confetti-style';
    style.textContent = `
      @keyframes confetti-fall {
        to { transform: translateY(110vh) rotate(720deg); opacity: 0; }
      }
    `;
    document.head.appendChild(style);
  }

  setTimeout(() => container.remove(), 4000);
}

/* ========================================================
   18. WIZARD (configurateur services)
   ======================================================== */
function initWizard() {
  const wizard = document.getElementById('service-wizard');
  if (!wizard) return;

  const steps     = wizard.querySelectorAll('.wizard-step');
  const nextBtns  = wizard.querySelectorAll('[data-wizard-next]');
  const prevBtns  = wizard.querySelectorAll('[data-wizard-prev]');
  const indicators = wizard.querySelectorAll('.wizard-indicator');
  let current = 0;

  function show(index) {
    steps.forEach((s, i) => s.classList.toggle('hidden', i !== index));
    indicators.forEach((ind, i) => {
      ind.classList.toggle('active',    i === index);
      ind.classList.toggle('completed', i < index);
    });
    current = index;
  }

  nextBtns.forEach(btn => btn.addEventListener('click', () => { if (current < steps.length - 1) show(current + 1); }));
  prevBtns.forEach(btn => btn.addEventListener('click', () => { if (current > 0) show(current - 1); }));

  show(0);
}

/* ========================================================
   19. SPOTLIGHT MOUSE TRACKING (service cards, glass-card)
   ======================================================== */
function initSpotlight() {
  const spotlightEls = document.querySelectorAll(
    '.service-card, .glass-card, .card.spotlight-card, .active-stat-card'
  );
  if (!spotlightEls.length) return;

  spotlightEls.forEach(el => {
    el.addEventListener('mousemove', e => {
      const rect = el.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width  * 100).toFixed(1) + '%';
      const y = ((e.clientY - rect.top)  / rect.height * 100).toFixed(1) + '%';
      el.style.setProperty('--mx', x);
      el.style.setProperty('--my', y);
    }, { passive: true });
  });
}

/* ========================================================
   20. RIPPLE EFFECT on buttons
   ======================================================== */
function initRipple() {
  document.addEventListener('click', e => {
    const btn = e.target.closest('.btn');
    if (!btn) return;

    const rect   = btn.getBoundingClientRect();
    const size   = Math.max(rect.width, rect.height) * 2;
    const x      = e.clientX - rect.left - size / 2;
    const y      = e.clientY - rect.top  - size / 2;

    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    ripple.style.cssText = `width:${size}px;height:${size}px;left:${x}px;top:${y}px`;
    btn.appendChild(ripple);
    ripple.addEventListener('animationend', () => ripple.remove());
  });
}

/* ========================================================
   21. SIDEBAR BACKDROP (mobile premium)
   ======================================================== */
function initSidebarPremium() {
  const sidebar    = document.getElementById('app-sidebar');
  const toggleBtns = document.querySelectorAll('[data-toggle-sidebar]');
  if (!sidebar) return;

  // Créer le backdrop s'il n'existe pas
  let backdrop = document.getElementById('sidebar-backdrop');
  if (!backdrop) {
    backdrop = document.createElement('div');
    backdrop.id = 'sidebar-backdrop';
    backdrop.className = 'sidebar-backdrop';
    document.body.appendChild(backdrop);
  }

  function openSidebar() {
    sidebar.classList.add('open');
    backdrop.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    backdrop.classList.remove('show');
    document.body.style.overflow = '';
  }

  toggleBtns.forEach(btn => {
    btn.addEventListener('click', e => {
      e.stopPropagation();
      sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
    });
  });

  backdrop.addEventListener('click', closeSidebar);

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeSidebar();
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth >= 1024) closeSidebar();
  }, { passive: true });
}

/* ========================================================
   22. ANIMATED HUB STATS (count up on load)
   ======================================================== */
function initHubCounters() {
  const vals = document.querySelectorAll('.active-stat-val');
  if (!vals.length) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting || entry.target.dataset.animated) return;
      entry.target.dataset.animated = '1';

      const el    = entry.target;
      // Extract numeric part from text like "5 commandes"
      const text  = el.textContent;
      const match = text.match(/^(\d+)/);
      if (!match) return;
      const end  = parseInt(match[1], 10);
      const suffix = text.slice(match[0].length); // " commandes" etc.

      const duration = 1000;
      const start    = performance.now();

      function tick(now) {
        const t  = Math.min((now - start) / duration, 1);
        const ease = 1 - Math.pow(1 - t, 3);
        el.innerHTML = `${Math.round(ease * end)}<span>${suffix}</span>`;
        if (t < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  }, { threshold: 0.5 });

  vals.forEach(v => observer.observe(v));
}

/* ========================================================
   23. STAGGER REVEAL (section categories on scroll)
   ======================================================== */
function initStaggerReveal() {
  const sections = document.querySelectorAll('.services-section > div');
  if (!sections.length) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -20px 0px' });

  sections.forEach((s, i) => {
    s.style.opacity = '0';
    s.style.transform = 'translateY(20px)';
    s.style.transition = `opacity 0.5s ease ${i * 0.06}s, transform 0.5s ease ${i * 0.06}s`;
    observer.observe(s);
  });
}

/* ========================================================
   19. INITIALISATION GLOBALE
   ======================================================== */
document.addEventListener('DOMContentLoaded', () => {
  initParticles();
  initCounters();
  initScrollNav();
  initScrollAnimations();
  initMobileMenu();
  initTestimonialSlider();
  initNavDropdowns();
  Modal.init();
  initCart();
  initSidebar();
  initSidebarPremium();   // remplace initSidebar pour mobile premium
  initTabs();
  initFilters();
  initCourseProgress();
  initSearchOverlay();
  initWizard();

  // Premium layer
  initSpotlight();
  initRipple();
  initHubCounters();
  initStaggerReveal();

  // Messages Django → Toasts automatiques
  document.querySelectorAll('[data-django-message]').forEach(el => {
    const type = el.dataset.djangoMessage || 'info';
    const text = el.textContent.trim();
    if (text) Toasts[type]?.(text) || Toasts.info(text);
    el.remove();
  });
});

/* Exporter pour usage manuel */
window.EShelle = {
  Toasts,
  Modal,
  aiStream,
  launchConfetti,
  copyToClipboard,
  formatFcfa,
  animateAddToCart,
  ajax,
};
