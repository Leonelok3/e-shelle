(function(){
  const $ = (s,r=document)=>r.querySelector(s);
  const $$ = (s,r=document)=>Array.from(r.querySelectorAll(s));

  document.addEventListener('DOMContentLoaded', ()=>{
    const y = document.getElementById('year');
    if (y) y.textContent = new Date().getFullYear();
  });

  document.addEventListener('click', (e)=>{
    const burger = e.target.closest('#menuToggle');
    const menu = $('#navMenu');
    if (burger && menu){
      const open = menu.classList.toggle('is-open');
      burger.setAttribute('aria-expanded', String(open));
    }
    if (e.target.matches('[data-close-modal], .modal__backdrop')){
      const modal = e.target.closest('.modal') || document.getElementById('modal-demo');
      if (modal) modal.hidden = true;
    }
    const openBtn = e.target.closest('[data-open-modal]');
    if (openBtn){
      const id = openBtn.getAttribute('data-open-modal');
      const m = document.getElementById(`modal-${id}`);
      if (m) m.hidden = false;
    }
  });

  document.addEventListener('change', (e)=>{
    if (e.target.id === 'langSwitch'){
      window.I97_I18N.applyLang(e.target.value);
    }
  });

  // micro-anim cartes
  $$('.card').forEach(c=>{
    c.addEventListener('mouseenter',()=> c.style.transform='translateY(-3px)');
    c.addEventListener('mouseleave',()=> c.style.transform='');
  });
})();


// --- Loader pendant le submit du formulaire photos ---
document.addEventListener('submit', (e)=>{
  const form = e.target;
  if (form.matches('[data-photo-form]')) {
    const btn = form.querySelector('button[type="submit"]');
    const wrap = form.querySelector('.progress-wrap');
    btn?.setAttribute('disabled', 'true');
    wrap && (wrap.style.display = 'block');
    // Laisse le submit natif faire la redirection 302 vers /result/<uuid>/
  }
});


// --- Empêche la soumission sans fichier ---
document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("[data-photo-form]");
  if (!form) return;
  const fileInput = form.querySelector('input[type="file"]');
  const submitBtn = form.querySelector('button[type="submit"]');

  if (fileInput && submitBtn) {
    submitBtn.disabled = true;
    fileInput.addEventListener("change", () => {
      submitBtn.disabled = !fileInput.files.length;
    });
  }
});


document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("navToggle");
  const navbar = document.querySelector(".navbar");

  if (toggle && navbar) {
    toggle.addEventListener("click", () => {
      navbar.classList.toggle("open");
    });
  }
});


document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('a[href*="billing"]').forEach(btn => {
    btn.addEventListener("click", () => {
      if (window.gtag) {
        gtag('event', 'cta_click', {
          event_category: 'conversion',
          event_label: 'billing_access'
        });
      }
    });
  });
});


document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('a[href*="billing"]').forEach(btn => {
    btn.addEventListener("click", () => {
      if (window.fbq) {
        fbq('track', 'InitiateCheckout');
      }
    });
  });
});


document.addEventListener("DOMContentLoaded", function () {
  const navToggle = document.getElementById("navToggle");
  const navMenu = document.querySelector(".navbar__nav");
  const userBtn = document.getElementById("userMenuBtn");
  const userDropdown = document.getElementById("userDropdown");

  // 🔥 Menu mobile principal
  if (navToggle && navMenu) {
    navToggle.addEventListener("click", function () {
      navMenu.classList.toggle("is-open");
    });
  }

  // 👤 Menu utilisateur
  if (userBtn && userDropdown) {
    userBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      userDropdown.classList.toggle("is-open");
    });

    document.addEventListener("click", function () {
      userDropdown.classList.remove("is-open");
    });
  }
});


/* =====================================================
   NAVBAR MOBILE TOGGLE — SAFE
===================================================== */
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".c-navbar__toggle");
  const nav = document.querySelector(".c-navbar__nav");

  if (!toggle || !nav) return;

  toggle.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
  });
});

document.querySelectorAll(".c-nav-link").forEach(link => {
  link.addEventListener("click", () => {
    nav.classList.remove("is-open");
    toggle.setAttribute("aria-expanded", "false");
  });
});


document.addEventListener("DOMContentLoaded", function () {
  const wrap = document.querySelector(".nl-global");
  if (!wrap) return;

  const KEY = "imm97_newsletter_closed_v1";
  const closeBtn = wrap.querySelector(".nl-global__close");

  // Si déjà fermé avant => ne pas afficher
  if (localStorage.getItem(KEY) === "1") {
    wrap.classList.add("is-hidden");
    return;
  }

  // Optionnel: éviter l’apparition immédiate (plus premium)
  // wrap.classList.add("is-hidden");
  // setTimeout(() => wrap.classList.remove("is-hidden"), 600);

  if (closeBtn) {
    closeBtn.addEventListener("click", function () {
      localStorage.setItem(KEY, "1");
      wrap.classList.add("is-closing");
      // après l’anim, on cache
      setTimeout(() => {
        wrap.classList.add("is-hidden");
      }, 360);
    });
  }
});



document.addEventListener("DOMContentLoaded", function () {
  const wrap = document.getElementById("nl-global");
  const closeBtn = document.getElementById("nl-close");
  if (!wrap || !closeBtn) return;

  // ✅ cooldown: si l'utilisateur ferme, on cache X heures puis ça revient
  const KEY = "imm97_newsletter_dismissed_until_v1";
  const COOLDOWN_HOURS = 6; // <- change à 24 si tu veux 1 jour

  const now = Date.now();
  const dismissedUntil = parseInt(localStorage.getItem(KEY) || "0", 10);

  // Si encore dans le cooldown => ne pas afficher
  if (dismissedUntil && now < dismissedUntil) {
    wrap.classList.add("is-hidden");
    wrap.setAttribute("aria-hidden", "true");
    return;
  }

  let shown = false;

  const show = () => {
    if (shown) return;
    shown = true;

    wrap.classList.remove("is-hidden");
    wrap.setAttribute("aria-hidden", "false");

    // petit hack repaint (stabilité sur certains navigateurs)
    requestAnimationFrame(() => {
      wrap.classList.remove("is-hidden");
    });
  };

  // ✅ Affiche après un scroll léger
  const onScroll = () => {
    const sc = window.scrollY || document.documentElement.scrollTop || 0;
    if (sc > 220) show();
  };
  window.addEventListener("scroll", onScroll, { passive: true });

  // ✅ Fallback : si page courte (pas assez de scroll) OU navigateur capricieux
  // Affiche après 4 secondes si rien ne s'est déclenché
  setTimeout(() => {
    // Si pas de scroll possible, ou juste pour assurer l'apparition
    const pageScrollable = (document.documentElement.scrollHeight - window.innerHeight) > 60;
    if (!shown) {
      if (!pageScrollable) show();
      else show(); // tu peux retirer ce else si tu veux uniquement scroll
    }
  }, 4000);

  // ✅ Fermeture : cache temporaire (pas permanent)
  closeBtn.addEventListener("click", function () {
    const until = Date.now() + COOLDOWN_HOURS * 60 * 60 * 1000;
    localStorage.setItem(KEY, String(until));

    wrap.classList.add("is-closing");
    setTimeout(() => {
      wrap.classList.add("is-hidden");
      wrap.setAttribute("aria-hidden", "true");
    }, 360);
  });
});
