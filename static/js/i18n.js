(function () {
  const dict = {
    fr: {
      app_name:"Immigration97", brand_name:"Immigration97",
      skip_to_content:"Aller au contenu",
      nav_features:"Fonctionnalités", nav_pricing:"Tarifs", nav_faq:"FAQ",
      change_language:"Changer de langue", login:"Connexion", signup:"Créer un compte",
      hero_title:"Votre voie rapide pour immigrer facilement :Génère une  photos visa, un CV, une lettres de motivation en un clic & decouvre tous les guides pour faciliter ta procedure d'immigration",
      hero_subtitle:"Une plateforme modulaire, bilingue et professionnelle pour accélérer vos démarches (DV-Lottery, études, travail, RP, paiement).",
      cta_get_started:"Commencer", cta_watch_demo:"Voir une démo",
      b1:"Export 600×600 DV-Lottery", b2:"CV & Lettres via IA", b3:"Guides visa & checklists", b4:"Paiement par service",
      badge_bilingual:"Bilingue FR/EN", card_fast:"Rapide & Automatisé", card_fast_desc:"Résultats en moins d’une minute par service.",
      open:"Ouvrir",
      m1_title:"generateur de photo visa", m1_desc:"Photos conformes (taille, fond, format) + validation auto.",
      m2_title:"Generateur de cv", m2_desc:"CV pro depuis formulaire ou import, multi-templates.",
      m3_title:"Generateur de lettre motivation", m3_desc:"Templates & génération IA (OpenAI) avec conseils.",
      m4_title:"Guide Visa Tourisme", m4_desc:"Documents requis, lettre d’invitation, étapes clés.",
      m5_title:"Visa Études", m5_desc:"Analyse profil, universités, checklist et RDV ambassade.",
      m6_title:"Visa Travail", m6_desc:"Offres adaptées, sites emplois, préparation entretien.",
      m7_title:"Préparation des Tests de Langue", m7_desc:"Exercices FR/EN/DE, corrigés, PDF/Audio/Vidéo.",
      m8_title:"Résidence Permanente", m8_desc:"Guides pays (ex Canada), checklists, estimation.",
      m9_title:"Système de Paiement", m9_desc:"Micropaiements, plans, Stripe/PayPal (hooks prêts).",
      pricing_title:"Tarifs simples", pricing_desc:"Micropaiement par service (1$) — facturation au clic, reçus e-mail.",
      price_starter:"Starter", per_job:"par service", buy_now:"Acheter",
      price_pro:"Pro", per_month:"/ mois", see_plans:"Voir les plans",
      faq_title:"FAQ", faq_q1:"Comment fonctionnent les crédits ?", faq_a1:"Chaque service consomme 1 crédit. Vous pouvez recharger via Stripe/PayPal.",
      faq_q2:"Puis-je utiliser mes propres modèles de CV ?", faq_a2:"Oui, importez votre CV, nous générons un template similaire.",
      footer_tag:"Plateforme modulaire pour l’immigration.",
      legal:"Mentions légales", contact:"Contact", privacy:"Confidentialité", all_rights:"Tous droits réservés.",
      demo_title:"Démo rapide", demo_body:"Cette vidéo/animation présentera le parcours type (bientôt).", close:"Fermer"
      working: "Génération en cours…",
    },
    en: {
      app_name:"Immigration97", brand_name:"Immigration97",
      skip_to_content:"Skip to content",
      nav_features:"Features", nav_pricing:"Pricing", nav_faq:"FAQ",
      change_language:"Change language", login:"Log in", signup:"Sign up",
      hero_title:"Your fast track to immigrate: photos, CVs, letters & guides",
      hero_subtitle:"A modular, bilingual, professional platform to accelerate your journey (DV-Lottery, study, work, PR, payments).",
      cta_get_started:"Get started", cta_watch_demo:"Watch a demo",
      b1:"DV-Lottery 600×600 export", b2:"CVs & Letters with AI", b3:"Visa guides & checklists", b4:"Pay per service",
      badge_bilingual:"Bilingual FR/EN", card_fast:"Fast & Automated", card_fast_desc:"Results in under a minute per service.",
      open:"Open",
      m1_title:"Visa Photo Generator", m1_desc:"Compliant photos (size, background, format) + auto-validation.",
      m2_title:"CV Generator", m2_desc:"Professional CV from form or import, multi-templates.",
      m3_title:"Motivation Letter Generator", m3_desc:"Templates & AI generation (OpenAI) with tips.",
      m4_title:"Tourist Visa Guide", m4_desc:"Required documents, invitation letter, key steps.",
      m5_title:"Study Visa", m5_desc:"Profile analysis, universities, checklist & embassy booking.",
      m6_title:"Work Visa", m6_desc:"Tailored offers, job boards, interview prep.",
      m7_title:"Language Test Prep", m7_desc:"FR/EN/DE exercises, answers, PDF/Audio/Video.",
      m8_title:"Permanent Residence", m8_desc:"Country guides (e.g., Canada), checklists, estimate.",
      m9_title:"Payment System", m9_desc:"Micropayments, plans, Stripe/PayPal (hooks ready).",
      pricing_title:"Simple pricing", pricing_desc:"Pay per service ($1) — per-click billing, email receipts.",
      price_starter:"Starter", per_job:"per service", buy_now:"Buy now",
      price_pro:"Pro", per_month:"/ month", see_plans:"See plans",
      faq_title:"FAQ", faq_q1:"How do credits work?", faq_a1:"Each service costs 1 credit. Top up via Stripe/PayPal.",
      faq_q2:"Can I use my own CV templates?", faq_a2:"Yes, upload your CV and we’ll generate a similar template.",
      footer_tag:"Modular platform for immigration.",
      legal:"Legal", contact:"Contact", privacy:"Privacy", all_rights:"All rights reserved.",
      demo_title:"Quick demo", demo_body:"This video/animation will show the typical flow (coming soon).", close:"Close"
      working: "Generating…",
    }
  };

  const $ = (s,r=document)=>r.querySelector(s);
  const $$ = (s,r=document)=>Array.from(r.querySelectorAll(s));

  function detectLang(){
    const stored = localStorage.getItem('lang');
    if (stored) return stored;
    const nav = (navigator.language || 'fr').slice(0,2);
    return nav === 'en' ? 'en' : 'fr';
  }
  function applyLang(lang){
    const t = dict[lang] || dict.fr;
    $$("[data-i18n-key]").forEach(node=>{
      const key = node.getAttribute("data-i18n-key");
      if (t[key]) node.textContent = t[key];
    });
    document.documentElement.lang = lang;
    localStorage.setItem('lang', lang);
    const select = $('#langSwitch');
    if (select) select.value = lang;
  }

  window.I97_I18N = { applyLang, detectLang };
  document.addEventListener('DOMContentLoaded', ()=> applyLang(detectLang()));
})();


