const VERSION = '__VERSION__';
const SHELL = `starjump-shell-${VERSION}`;
const RUNTIME = 'starjump-runtime-pygbag-0.9.3';
const FILES = ['./', './index.html', './boot.js?v=__VERSION__', './manifest.webmanifest', './icons/icon-192.png', './icons/icon-512.png', './icons/apple-touch-icon.png', (self.location.hostname.endsWith('.itch.zone') ? './stage.apk' : './stage.tar.gz'), './vendor/browserfs.min.js'];
let pending = new Set();
let failed = false;
self.addEventListener('install', event => event.waitUntil((async () => {
  await (await caches.open(SHELL)).addAll(FILES);
  await self.skipWaiting();
})()));
self.addEventListener('activate', event => event.waitUntil((async () => {
  for (const name of await caches.keys()) {
    if (name.startsWith('starjump-shell-') && name !== SHELL) await caches.delete(name);
  }
  await self.clients.claim();
})()));
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET') return;
  const local = url.origin === self.location.origin && url.pathname.startsWith(self.registration.scope.replace(url.origin, ''));
  const runtime = url.origin === 'https://pygame-web.github.io';
  if (!local && !runtime) return;
  const task = (async () => {
    const cache = await caches.open(local ? SHELL : RUNTIME);
    const key = request.mode === 'navigate' ? new Request(self.registration.scope) : request;
    if (request.mode === 'navigate') {
      try {
        const fresh = await fetch(request);
        if (fresh.ok) { await cache.put(key, fresh.clone()); return fresh; }
      } catch (_) { /* offline: use the saved game shell */ }
    }
    const hit = await cache.match(key);
    if (hit) return hit;
    const response = await fetch(request);
    if (response.ok || response.type === 'opaque') {
      try { await cache.put(key, response.clone()); } catch (error) { failed = true; console.warn('StarJump cache write failed', request.url, error); }
    }
    return response;
  })();
  pending.add(task);
  // waitUntil keeps the worker alive until the cache write is durable.
  event.waitUntil(task.catch(() => {failed = true;}).finally(() => pending.delete(task)));
  event.respondWith(task);
});
self.addEventListener('message', event => {
  if (event.data?.type !== 'READY') return;
  event.waitUntil((async () => {
    await Promise.allSettled([...pending]);
    event.source?.postMessage({type:failed ? 'CACHE_INCOMPLETE' : 'OFFLINE_READY'});
  })());
});
