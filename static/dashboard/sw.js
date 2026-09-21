const CACHE='sigma-shell-v424';
const ASSETS=['/dashboard/','/dashboard/index.html','/dashboard/assets/sigma.css','/dashboard/assets/sigma.js','/dashboard/manifest.webmanifest'];
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('sigma-shell-')&&k!=='sigma-shell-v424').map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{if(e.request.method!=='GET'||!e.request.url.startsWith(self.location.origin))return;e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)))});
