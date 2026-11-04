const CACHE='folio-shell-v53-saved-filter-views';
const FILES=['./','./index.html','./styles.css','./app.js','./core.js','./demo.json','./manifest.webmanifest','./icons/icon.svg','./icons/icon-192.png','./icons/icon-512.png','./offline.html','./assets/icons/nav-sprite.webp','./assets/icons/feature-sprite.webp','./assets/illustrations/featured-empty-folio.webp','./assets/covers/portfolio-studio.webp','./assets/covers/cleaning-crm.webp','./assets/covers/city-courtyards.webp'];
self.addEventListener('install',e=>e.waitUntil((async()=>{
  const cache=await caches.open(CACHE);
  await Promise.all(FILES.map(async path=>{
    const separator=path.includes('?')?'&':'?';
    const request=new Request(`${path}${separator}__folio=${encodeURIComponent(CACHE)}`,{cache:'reload'});
    const response=await fetch(request);
    if(!response.ok)throw new Error(`Precache failed for ${path}: ${response.status}`);
    await cache.put(path,response);
  }));
  await self.skipWaiting();
})()));
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('folio-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{
  const request=e.request;
  if(request.method!=='GET'||new URL(request.url).origin!==self.location.origin)return;
  e.respondWith((async()=>{
    const cache=await caches.open(CACHE);
    const cached=await cache.match(request);
    if(cached)return cached;
    try{
      const response=await fetch(request);
      if(response.ok&&response.type!=='opaque'&&new URL(response.url||request.url).origin===self.location.origin)await cache.put(request,response.clone());
      return response;
    }catch{
      if(request.mode==='navigate')return await cache.match('./offline.html')||Response.error();
      return Response.error();
    }
  })());
});







