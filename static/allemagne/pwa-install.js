document.addEventListener('DOMContentLoaded', () => {
  // 1. Enregistrement du Service Worker
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/allemagne/sw.js', { scope: '/allemagne/' })
      .then(reg => console.log('PWA Service Worker enregistré (scope: ' + reg.scope + ')'))
      .catch(err => console.error('Erreur enregistrement SW:', err));
  }

  // 2. Variables de contrôle
  let deferredPrompt;
  const storageKey = 'pwa_prompt_dismissed';

  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
  const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;

  // Si déjà installé ou déjà fermé dans cette session
  if (isStandalone || localStorage.getItem(storageKey)) {
    return;
  }

  // 3. Création et injection du style CSS de la bannière
  const style = document.createElement('style');
  style.innerHTML = `
    .pwa-banner {
      position: fixed;
      bottom: 20px;
      right: 20px;
      left: 20px;
      max-width: 450px;
      background: rgba(17, 24, 39, 0.95);
      border: 1px solid rgba(227, 0, 15, 0.4);
      border-radius: 16px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
      backdrop-filter: blur(12px);
      z-index: 10000;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      transform: translateY(150%);
      transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
      font-family: 'Plus Jakarta Sans', sans-serif;
      color: #e5e7eb;
    }
    @media (min-width: 576px) {
      .pwa-banner {
        left: auto;
      }
    }
    .pwa-banner.show {
      transform: translateY(0);
    }
    .pwa-header {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .pwa-logo {
      width: 48px;
      height: 48px;
      border-radius: 10px;
      object-fit: cover;
      border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .pwa-title-container {
      flex: 1;
    }
    .pwa-title {
      font-weight: 700;
      font-size: 1rem;
      margin: 0;
      color: #ffffff;
    }
    .pwa-desc {
      font-size: 0.8rem;
      margin: 2px 0 0;
      color: #9ca3af;
      line-height: 1.3;
    }
    .pwa-close {
      background: none;
      border: none;
      color: #9ca3af;
      cursor: pointer;
      font-size: 1.2rem;
      padding: 4px;
      line-height: 1;
      transition: color 0.2s;
    }
    .pwa-close:hover {
      color: #ffffff;
    }
    .pwa-actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
    }
    .pwa-btn {
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
    }
    .pwa-btn-dismiss {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #e5e7eb;
    }
    .pwa-btn-dismiss:hover {
      background: rgba(255, 255, 255, 0.15);
    }
    .pwa-btn-install {
      background: #E3000F;
      border: 1px solid #E3000F;
      color: #ffffff;
    }
    .pwa-btn-install:hover {
      background: #b91c1c;
      border-color: #b91c1c;
      box-shadow: 0 4px 12px rgba(227, 0, 15, 0.3);
    }
    .pwa-ios-instructions {
      font-size: 0.8rem;
      color: #d1d5db;
      background: rgba(255, 255, 255, 0.05);
      padding: 8px 12px;
      border-radius: 8px;
      border-left: 3px solid #ffce00;
      margin-top: 4px;
      line-height: 1.4;
    }
  `;
  document.head.appendChild(style);

  // 4. Création des éléments HTML de la bannière
  const banner = document.createElement('div');
  banner.className = 'pwa-banner';
  banner.innerHTML = `
    <div class="pwa-header">
      <img src="/static/img/logo.png" alt="E-Shelle Logo" class="pwa-logo">
      <div class="pwa-title-container">
        <p class="pwa-title">E-Shelle Allemagne</p>
        <p class="pwa-desc">Installez l'application pour accéder rapidement à vos cours et offres d'emploi.</p>
      </div>
      <button class="pwa-close" id="pwa-close-btn">&times;</button>
    </div>
    <div id="pwa-body-content"></div>
    <div class="pwa-actions" id="pwa-actions-container">
      <button class="pwa-btn pwa-btn-dismiss" id="pwa-btn-cancel">Plus tard</button>
    </div>
  `;
  document.body.appendChild(banner);

  const bodyContent = document.getElementById('pwa-body-content');
  const actionsContainer = document.getElementById('pwa-actions-container');

  // Gestion de la fermeture
  const dismissPwa = () => {
    banner.classList.remove('show');
    localStorage.setItem(storageKey, 'true');
  };
  document.getElementById('pwa-close-btn').addEventListener('click', dismissPwa);
  document.getElementById('pwa-btn-cancel').addEventListener('click', dismissPwa);

  // 5. Logique Android/Chrome (Prompt standard)
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;

    // Ajouter le bouton d'installation
    if (!document.getElementById('pwa-btn-install-action')) {
      const installBtn = document.createElement('button');
      installBtn.className = 'pwa-btn pwa-btn-install';
      installBtn.id = 'pwa-btn-install-action';
      installBtn.innerText = 'Installer';
      actionsContainer.appendChild(installBtn);

      installBtn.addEventListener('click', () => {
        banner.classList.remove('show');
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
          if (choiceResult.outcome === 'accepted') {
            console.log('Utilisateur a accepté l\'installation de la PWA');
            localStorage.setItem(storageKey, 'true');
          } else {
            console.log('Utilisateur a décliné l\'installation de la PWA');
          }
          deferredPrompt = null;
        });
      });
    }

    // Afficher la bannière
    setTimeout(() => banner.classList.add('show'), 2000);
  });

  // 6. Logique iOS/Safari
  if (isIOS && isSafari) {
    bodyContent.innerHTML = `
      <div class="pwa-ios-instructions">
        Appuyez sur le bouton <strong>Partager</strong> <span style="font-size:1.1rem; vertical-align:middle;">⎋</span> en bas de Safari, puis sélectionnez <strong>Sur l'écran d'accueil</strong>.
      </div>
    `;
    setTimeout(() => banner.classList.add('show'), 2000);
  }
});
