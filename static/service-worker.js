const CACHE_VERSION = "pokemon-pvp-v4";
const APP_CACHE = `${CACHE_VERSION}-app`;
const RUNTIME_CACHE = `${CACHE_VERSION}-runtime`;
const IMAGE_CACHE = `${CACHE_VERSION}-images`;

const PRECACHE_URLS = [
    "/",
    "/manifest.json",
    "/static/offline.html",
    "/static/style.css",
    "/static/app.js",
    "/static/192x192.png",
    "/static/512x512.png"
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(APP_CACHE)
            .then(cache => cache.addAll(PRECACHE_URLS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener("activate", event => {
    const expectedCaches = new Set([APP_CACHE, RUNTIME_CACHE, IMAGE_CACHE]);
    event.waitUntil(
        caches.keys()
            .then(keys => Promise.all(keys.map(key => {
                if (!expectedCaches.has(key) && key.startsWith("pokemon-pvp-")) {
                    return caches.delete(key);
                }
                return Promise.resolve();
            })))
            .then(() => self.clients.claim())
    );
});

self.addEventListener("fetch", event => {
    const request = event.request;
    if (request.method !== "GET") return;

    const url = new URL(request.url);

    if (request.mode === "navigate") {
        event.respondWith(networkFirst(request, APP_CACHE, "/static/offline.html"));
        return;
    }

    if (url.origin === self.location.origin && url.pathname.startsWith("/api/")) {
        event.respondWith(networkFirst(request, RUNTIME_CACHE));
        return;
    }

    if (isImageRequest(request)) {
        event.respondWith(cacheFirst(request, IMAGE_CACHE));
        return;
    }

    if (isStaticAsset(request, url)) {
        event.respondWith(cacheFirst(request, RUNTIME_CACHE));
    }
});

function isImageRequest(request) {
    return request.destination === "image";
}

function isStaticAsset(request, url) {
    if (url.origin === self.location.origin) {
        return url.pathname.startsWith("/static/")
            || url.pathname === "/manifest.json"
            || url.pathname === "/service-worker.js";
    }
    return ["script", "style", "font"].includes(request.destination);
}

async function cacheFirst(request, cacheName) {
    const cached = await caches.match(request);
    if (cached) return cached;

    const response = await fetch(request);
    await cacheIfUsable(request, response, cacheName);
    return response;
}

async function networkFirst(request, cacheName, fallbackUrl = null) {
    try {
        const response = await fetch(request);
        await cacheIfUsable(request, response, cacheName);
        return response;
    } catch (error) {
        const cached = await caches.match(request);
        if (cached) return cached;
        if (fallbackUrl) {
            const fallback = await caches.match(fallbackUrl);
            if (fallback) return fallback;
        }
        throw error;
    }
}

async function cacheIfUsable(request, response, cacheName) {
    if (!response || !(response.ok || response.type === "opaque")) return;
    const cache = await caches.open(cacheName);
    await cache.put(request, response.clone());
}
