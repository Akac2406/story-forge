// Offline shell only. Never persist arbitrary story, API, or user-data responses.
const CACHE = "sf-v90";
const APP_FILES = [
  "./", "index.html", "listen.html", "manifest.webmanifest",
  "illustrated-reader.css", "memory-engine.js", "canon-engine.js", "icon-192.png", "icon-512.png",
  "visual-customization-v48.js", "visual-customization-v48.css",
  "cinematic-ui-v49.js", "cinematic-ui-v49.css",
  "character-ui-v50.js", "character-ui-v50.css",
  "character-studio-v51.js", "character-studio-v51.css",
  "relationship-map-v52.js", "relationship-map-v52.css",
  "cinematic-profiles-v53.js", "cinematic-profiles-v53.css",
  "cinematic-scenes-v54.js", "cinematic-scenes-v54.css",
];
const APP_PATHS = new Set(APP_FILES.map(file => new URL(file, self.registration.scope).pathname));

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(APP_FILES))
    .then(() => self.skipWaiting()));
});

self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(key => /^sf-v/.test(key) && key !== CACHE).map(key => caches.delete(key))
  )).then(() => self.clients.claim()));
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin || url.search ||
      !APP_PATHS.has(url.pathname) || request.headers.has("range")) return;

  // A response can be cached only if it is a successful, non-redirected static asset.
  event.respondWith((async () => {
    try {
      const response = await fetch(request);
      if (response.ok && !response.redirected && response.type !== "opaque") {
        const copy = response.clone();
        event.waitUntil(caches.open(CACHE).then(cache => cache.put(request, copy)).catch(() => {}));
      }
      return response;
    } catch (error) {
      const cached = await (await caches.open(CACHE)).match(request);
      if (cached) return cached;
      throw error;
    }
  })());
});
