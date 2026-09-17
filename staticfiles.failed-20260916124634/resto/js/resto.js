/**
 * E-Shelle Resto — Main JavaScript
 * Alpine.js components + HTMX helpers
 */

// ── Global toast system ────────────────────────────────────────────────────────
let _toastId = 0;

window.restoToast = function (message, type = 'success') {
  // Find the Alpine component root and push to its toasts array
  const appEl = document.querySelector('[x-data="restoApp()"]');
  if (appEl && appEl._x_dataStack) {
    const data = appEl._x_dataStack[0];
    if (data && data.toasts !== undefined) {
      const id = ++_toastId;
      data.toasts.push({ id, message, type, visible: true });
      setTimeout(() => {
        const toast = data.toasts.find(t => t.id === id);
        if (toast) toast.visible = false;
        setTimeout(() => {
          data.toasts = data.toasts.filter(t => t.id !== id);
        }, 200);
      }, 4000);
    }
  }
};

// ── Main Alpine.js app component ───────────────────────────────────────────────
function restoApp() {
  return {
    toasts: [],

    addToast(message, type = 'success') {
      const id = ++_toastId;
      this.toasts.push({ id, message, type, visible: true });
      setTimeout(() => {
        const t = this.toasts.find(t => t.id === id);
        if (t) t.visible = false;
        setTimeout(() => {
          this.toasts = this.toasts.filter(t => t.id !== id);
        }, 200);
      }, 4000);
    },

    removeToast(id) {
      const t = this.toasts.find(t => t.id === id);
      if (t) t.visible = false;
      setTimeout(() => {
        this.toasts = this.toasts.filter(t => t.id !== id);
      }, 200);
    },
  };
}

// Expose so Django messages script can call it
document.addEventListener('alpine:init', () => {
  window.restoToast = function (message, type = 'success') {
    const appEl = document.querySelector('[x-data]');
    if (appEl && appEl.__x) {
      appEl.__x.$data.addToast(message, type);
    }
  };
});

// ── Contact tracking helper (called from inline onclick) ───────────────────────
function trackContact(restaurantId, action, dishId = null) {
  const data = new FormData();
  data.append('restaurant_id', restaurantId);
  data.append('action', action);
  if (dishId) data.append('dish_id', dishId);

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

  fetch('/resto/track/', {
    method: 'POST',
    headers: { 'X-CSRFToken': csrfToken },
    body: data,
  }).catch(() => {}); // Silent fail — tracking is non-critical
}

// ── HTMX event hooks ──────────────────────────────────────────────────────────
document.addEventListener('htmx:afterRequest', function (evt) {
  if (evt.detail.successful) {
    // Show skeleton loaders on HTMX request start
  }
});

document.addEventListener('htmx:beforeRequest', function (evt) {
  // Could add skeleton loaders here
});

document.addEventListener('htmx:responseError', function (evt) {
  console.error('HTMX request failed:', evt.detail.xhr.status);
});

// ── Lazy image observer (extra lazy loading support) ───────────────────────────
if ('IntersectionObserver' in window) {
  const imageObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const img = entry.target;
        if (img.dataset.src) {
          img.src = img.dataset.src;
          img.removeAttribute('data-src');
        }
        observer.unobserve(img);
      }
    });
  }, { rootMargin: '50px 0px' });

  document.querySelectorAll('img[data-src]').forEach(img => {
    imageObserver.observe(img);
  });
}

// ── Scroll to top on HTMX navigation ──────────────────────────────────────────
document.addEventListener('htmx:afterSwap', function (evt) {
  if (evt.detail.target.id === 'restaurant-grid') {
    evt.detail.target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
});

// ── Phone number formatting helper ────────────────────────────────────────────
function formatCameroonPhone(input) {
  let value = input.value.replace(/\s/g, '');
  if (!value.startsWith('+237') && value.startsWith('6')) {
    value = '+237 ' + value;
  }
  input.value = value;
}

// ── Copy share link helper ─────────────────────────────────────────────────────
function copyShareLink(url) {
  if (navigator.share) {
    navigator.share({ url });
  } else {
    navigator.clipboard.writeText(url).then(() => {
      window.restoToast && window.restoToast('Lien copié !', 'success');
    });
  }
}
