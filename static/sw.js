/* Immigration97 — Service Worker v1
   Stratégie : Network-First avec fallback cache
   Scope : / (toute l'app)
*/

const CACHE_NAME = 'imm97-v1';
const PRECACHE_URLS = [
  '/prep/fr/',
  '/static/css/preparation_tests.css',
  '/static/css/base.css',
  '/static/img/LOGOIMM97.png',
];

/* ── Install : pré-cache des ressources critiques ─── */
self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(PRECACHE_URLS);
    }).catch(function () {
      /* Silently ignore pre-cache errors (offline install) */
    })
  );
  self.skipWaiting();
});

/* ── Activate : purge des anciens caches ────────────── */
self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (cacheNames) {
      return Promise.all(
        cacheNames
          .filter(function (name) { return name !== CACHE_NAME; })
          .map(function (name) { return caches.delete(name); })
      );
    })
  );
  self.clients.claim();
});

/* ── Fetch : Network-First ──────────────────────────── */
self.addEventListener('fetch', function (event) {
  /* Ne traiter que les GET */
  if (event.request.method !== 'GET') return;

  /* Ignorer les requêtes non-http (chrome-extension, etc.) */
  if (!event.request.url.startsWith('http')) return;

  /* Ignorer les requêtes vers des domaines tiers (ads, CDN external) */
  var url = new URL(event.request.url);
  if (url.hostname !== self.location.hostname) return;

  event.respondWith(
    fetch(event.request)
      .then(function (networkResponse) {
        /* Mettre en cache si réponse valide */
        if (networkResponse && networkResponse.ok && networkResponse.type === 'basic') {
          var clone = networkResponse.clone();
          caches.open(CACHE_NAME).then(function (cache) {
            cache.put(event.request, clone);
          });
        }
        return networkResponse;
      })
      .catch(function () {
        /* Fallback cache */
        return caches.match(event.request).then(function (cached) {
          if (cached) return cached;
          /* Page hors-ligne de secours */
          return new Response(
            '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">'
            + '<meta name="viewport" content="width=device-width,initial-scale=1">'
            + '<title>Hors ligne — Immigration97</title>'
            + '<style>body{font-family:sans-serif;background:#0f172a;color:#e5e7eb;'
            + 'display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;}'
            + '.box{text-align:center;padding:2rem;}h1{color:#22c55e;}p{opacity:.75;}</style>'
            + '</head><body><div class="box">'
            + '<h1>📶 Connexion requise</h1>'
            + '<p>Immigration97 nécessite une connexion internet.</p>'
            + '<p>Reconnecte-toi pour continuer ta préparation.</p>'
            + '<a href="/" style="color:#22c55e;">Réessayer</a>'
            + '</div></body></html>',
            { headers: { 'Content-Type': 'text/html; charset=utf-8' } }
          );
        });
      })
  );
});
