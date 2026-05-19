const CACHE_NAME = 'v1';
const ASSETS = [
  '/',
  '/static/api.js',
  '/static/auth.js',
  '/static/ui.js',
  '/static/chat.js',
  '/static/auth.css',
  '/static/landing.css',
  '/static/base.css',
  '/static/chat.css'
];

self.addEventListener('install', e =>
  e.waitUntil(caches.open(CACHE_NAME).then(c => c.addAll(ASSETS)))
);

self.addEventListener('activate', e =>
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
  ))
);

self.addEventListener('fetch', e =>
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  )
);