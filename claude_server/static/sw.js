// Service Worker mínimo — cachea el shell (HTML/JS/CSS) para reabrir offline.
// Estrategia: network-first con fallback a cache para el shell.
// API (/inbox, /poll, /stream, /upload) NUNCA se cachea.

const SHELL_CACHE = "claude-bridge-shell-v1";
const SHELL_ASSETS = [
  "/",
  "/static/index.html",
  "/static/app.js",
  "/static/style.css",
  "/static/manifest.json",
  "/static/icon-192.png",
  "/static/icon-512.png",
  "/static/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter(k => k !== SHELL_CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Nunca tocar las rutas dinámicas.
  if (
    url.pathname.startsWith("/inbox") ||
    url.pathname.startsWith("/poll") ||
    url.pathname.startsWith("/stream") ||
    url.pathname.startsWith("/upload") ||
    url.pathname.startsWith("/uploads") ||
    url.pathname === "/health"
  ) {
    return; // fetch nativo
  }

  // Shell: network-first, fallback a cache.
  event.respondWith(
    fetch(event.request)
      .then((resp) => {
        // Solo cacheamos GET 200 OK del mismo origen.
        if (
          event.request.method === "GET" &&
          resp.ok &&
          resp.type === "basic"
        ) {
          const copy = resp.clone();
          caches.open(SHELL_CACHE).then((c) => c.put(event.request, copy));
        }
        return resp;
      })
      .catch(() => caches.match(event.request).then((m) => m || caches.match("/static/index.html")))
  );
});
