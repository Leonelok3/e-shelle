/**
 * i18n Connector — Charge et applique traductions basées sur data-lang
 */
(function(){
  const body = document.querySelector('body.home');
  if(!body) return;

  // Traductions pré-définies (extensible avec API)
  const translations = {
    fr: {
      hero_subtitle: 'Plan d\'action, guides officiels et accompagnement pas-à-pas pour réussir ton projet.',
    },
    en: {
      hero_subtitle: 'Action plan, official guides, and step-by-step support to make your immigration project a success.',
    },
    es: {
      hero_subtitle: 'Plan de acción, guías oficiales y apoyo paso a paso para lograr tu proyecto de inmigración.',
    },
  };

  function loadTranslations(){
    const lang = document.documentElement.getAttribute('lang') || body.getAttribute('data-lang') || 'fr';
    const trans = translations[lang] || translations['fr'];

    Object.keys(trans).forEach(key => {
      const els = document.querySelectorAll(`[data-i18n-key="${key}"]`);
      els.forEach(el => {
        el.textContent = trans[key];
      });
    });
  }

  // Init on load
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', loadTranslations);
  } else {
    loadTranslations();
  }

  // Watch for lang changes
  window.changeLanguage = function(lang){
    document.documentElement.setAttribute('lang', lang);
    body.setAttribute('data-lang', lang);
    loadTranslations();
  };
})();
