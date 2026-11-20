// Offline support: pages are cached on first visit and served when offline.
const CACHE = 'tokyo2612-v30';
const PRECACHE = ['./', 'index.html', 'manifest.json', 'apple-touch-icon.png', 'favicon.png'];
const FONT_HOSTS = ['fonts.googleapis.com', 'fonts.gstatic.com'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function networkFirst(req, timeoutMs) {
  return new Promise((resolve) => {
    let settled = false;
    const fallback = () => caches.match(req, { ignoreSearch: true }).then((r) => r || caches.match('index.html'));
    const timer = setTimeout(() => {
      fallback().then((r) => { if (r && !settled) { settled = true; resolve(r); } });
    }, timeoutMs);
    fetch(req).then((res) => {
      clearTimeout(timer);
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(req, copy));
      if (!settled) { settled = true; resolve(res); }
    }).catch(() => {
      clearTimeout(timer);
      fallback().then((r) => { if (!settled) { settled = true; resolve(r || Response.error()); } });
    });
  });
}

function cacheFirst(req) {
  return caches.match(req).then((hit) => hit || fetch(req).then((res) => {
    if (res && (res.ok || res.type === 'opaque')) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
    return res;
  }));
}

function staleWhileRevalidate(req) {
  return caches.match(req).then((hit) => {
    const net = fetch(req).then((res) => {
      if (res && res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
      return res;
    }).catch(() => hit);
    return hit || net;
  });
}

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (FONT_HOSTS.includes(url.hostname)) { e.respondWith(cacheFirst(req)); return; }
  if (url.origin !== location.origin) return;
  if (req.mode === 'navigate') { e.respondWith(networkFirst(req, 4000)); return; }
  e.respondWith(staleWhileRevalidate(req));
});
