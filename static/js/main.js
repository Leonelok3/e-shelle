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
