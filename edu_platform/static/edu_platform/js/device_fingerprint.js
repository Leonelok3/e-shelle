/**
 * EduCam Pro — Device Fingerprinting
 * Calcule un fingerprint composite côté client et l'envoie au serveur.
 * Ne collecte AUCUNE donnée personnelle, uniquement des caractéristiques
 * techniques de l'appareil pour la sécurité anti-partage.
 */

(function () {
  'use strict';

  /**
   * Collecte les composantes du fingerprint.
   * @returns {string} Chaîne concaténée de toutes les composantes.
   */
  function collectComponents() {
    const components = [];

    // User-Agent (navigateur et OS)
    components.push(navigator.userAgent || '');

    // Résolution et profondeur de couleur écran
    components.push(`${screen.width}x${screen.height}x${screen.colorDepth}`);

    // Fuseau horaire
    try {
      components.push(Intl.DateTimeFormat().resolvedOptions().timeZone);
    } catch (e) {
      components.push('unknown_tz');
    }

    // Nombre de cœurs CPU
    components.push(String(navigator.hardwareConcurrency || 0));

    // Mémoire RAM disponible (en Go, arrondi)
    components.push(String(navigator.deviceMemory || 0));

    // Langue navigateur
    components.push(navigator.language || '');

    // Plateforme
    components.push(navigator.platform || '');

    // Touch support
    components.push(String('ontouchstart' in window));

    return components.join('|');
  }

  /**
   * Calcule un hash SHA-256 d'une chaîne (Web Crypto API).
   * @param {string} message
   * @returns {Promise<string>} Hash hexadécimal
   */
  async function sha256(message) {
    const msgBuffer = new TextEncoder().encode(message);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  /**
   * Initialise le fingerprinting et stocke le hash dans un cookie
   * et dans un header pour les requêtes suivantes.
   */
  async function initFingerprint() {
    try {
      const raw = collectComponents();
      const fingerprint = await sha256(raw);

      // Stocker dans un cookie sécurisé (non HttpOnly car lu par JS)
      document.cookie = `edu_device_fp=${fingerprint}; path=/edu/; SameSite=Strict; max-age=86400`;

      // Envoyer via l'API de vérification si l'utilisateur est connecté
      // (seulement si on est dans /edu/ et authentifié)
      if (window.location.pathname.startsWith('/edu/') &&
          document.body.classList.contains('dashboard-page')) {
        sendFingerprintToServer(fingerprint);
      }

    } catch (err) {
      // Silencieux — ne pas bloquer l'expérience utilisateur
      console.warn('EduCam fingerprint error:', err);
    }
  }

  /**
   * Envoie le fingerprint au serveur pour vérification.
   * @param {string} fingerprint
   */
  function sendFingerprintToServer(fingerprint) {
    const csrfToken = getCookie('csrftoken');
    if (!csrfToken) return;

    fetch('/edu/api/device-check/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
        'X-Device-Fingerprint': fingerprint,
      },
      body: JSON.stringify({ fingerprint }),
    })
    .then(r => r.json())
    .then(data => {
      if (data.has_subscription && !data.device_ok && !data.needs_binding) {
        // Appareil non autorisé → redirection sécurité
        window.location.href = '/edu/device-blocked/';
      }
    })
    .catch(() => {}); // Silencieux
  }

  /**
   * Lit un cookie par son nom.
   * @param {string} name
   * @returns {string}
   */
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  }

  // Lancer au chargement de la page
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFingerprint);
  } else {
    initFingerprint();
  }

  // Animation fade-up au scroll
  function initScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll('.fade-up').forEach(el => observer.observe(el));
  }

  document.addEventListener('DOMContentLoaded', initScrollAnimations);

})();
