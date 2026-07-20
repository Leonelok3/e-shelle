const CACHE_NAME = 'eshelle-allemagne-v1';
const ASSETS_TO_CACHE = [
  '/allemagne/',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    })
  );
});

self.addEventListener('fetch', event => {
  const requestUrl = new URL(event.request.url);
  // Intercepter uniquement les requêtes de /allemagne/ ou les ressources statiques
  if (requestUrl.pathname.startsWith('/allemagne/') || requestUrl.pathname.startsWith('/static/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          if (event.request.method === 'GET' && response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, responseClone);
            });
          }
          return response;
        })
        .catch(() => {
          return caches.match(event.request);
        })
    );
  }
});
