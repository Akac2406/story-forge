const CACHE = "sf-v84";
const APP_FILES = [
  "./",
  "index.html",
  "illustrated-reader.css",
  "memory-engine.js",
  "icon-192.png",
  "visual-customization-v48.js",
  "visual-customization-v48.css",
  "cinematic-ui-v49.js",
  "cinematic-ui-v49.css",
  "character-ui-v50.js",
  "character-ui-v50.css",
  "character-studio-v51.js",
  "character-studio-v51.css",
  "relationship-map-v52.js",
  "relationship-map-v52.css",
  "cinematic-profiles-v53.js",
  "cinematic-profiles-v53.css",
  "cinematic-scenes-v54.js",
  "cinematic-scenes-v54.css",
];

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
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.origin !== location.origin || url.search) return;

  const network = fetch(event.request);
  event.waitUntil(network.then(response => {
    if (!response.ok) return;
    const copy = response.clone();
    return caches.open(CACHE).then(cache => cache.put(event.request, copy));
  }).catch(() => {}));
  event.respondWith(network.catch(async error => {
    const cache = await caches.open(CACHE);
    const saved = await cache.match(event.request);
    if (saved) return saved;
    throw error;
  }));
});
