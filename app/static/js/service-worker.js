/**
 * Service Worker for Meal Expense Tracker
 * Simplified offline support and caching
 *
 * @version 2.0.0
 * @author Meal Expense Tracker Team
 */

const CACHE_NAME = 'meal-tracker-v4';
const OFFLINE_URL = '/static/offline.html';

const IS_DEV_HOST = ['localhost', '127.0.0.1'].includes(self.location.hostname);

// Essential files to cache
const STATIC_FILES = [
  '/',
  '/static/css/main.css',
  '/static/js/app.js',
  OFFLINE_URL,
];

// ===== INSTALL EVENT =====

// ===== HELPER FUNCTIONS =====

/**
 * Check if request is for a static asset
 */
function isStaticAsset(url) {
  return url.pathname.startsWith('/static/') ||
         url.pathname.endsWith('.css') ||
         url.pathname.endsWith('.js') ||
         url.pathname.endsWith('.png') ||
         url.pathname.endsWith('.jpg') ||
         url.pathname.endsWith('.ico');
}

/**
 * Check if request is a navigation request
 */
function isNavigationRequest(request) {
  return request.mode === 'navigate' ||
         (request.method === 'GET' && request.headers.get('accept').includes('text/html'));
}

/**
 * Check if request is for API
 */
function isAPIRequest(url) {
  return url.pathname.startsWith('/api/') ||
         url.pathname.startsWith('/restaurants/') ||
         url.pathname.startsWith('/expenses/');
}

/**
 * Handle static asset requests (cache first)
 */
async function handleStaticAsset(request) {
  try {
    // In development, prefer fresh assets to avoid stale UI/JS during rapid iteration.
    if (IS_DEV_HOST) {
      const networkResponse = await fetch(request);
      if (networkResponse.ok) {
        const cache = await caches.open(CACHE_NAME);
        cache.put(request, networkResponse.clone());
      }
      return networkResponse;
    }

    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    const networkResponse = await fetch(request);

    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    console.warn('Static asset request failed:', error);

    // Return cached version if available
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    throw error;
  }
}

/**
 * Handle navigation requests (network first, cache fallback)
 */
async function handleNavigation(request) {
  try {
    const networkResponse = await fetch(request);

    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    console.warn('Navigation request failed, trying cache:', error);

    // Try cache first
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // Return offline page as last resort
    const offlineResponse = await caches.match(OFFLINE_URL);
    if (offlineResponse) {
      return offlineResponse;
    }

    throw error;
  }
}

/**
 * Handle API requests (network only with offline detection)
 */
async function handleAPI(request) {
  try {
    return await fetch(request);
  } catch (error) {
    console.warn('API request failed:', error);

    // Return a meaningful offline response
    return new Response(
      JSON.stringify({
        error: 'offline',
        message: 'This action requires an internet connection. Please try again when online.',
      }),
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: {
          'Content-Type': 'application/json',
        },
      },
    );
  }
}

// ===== INSTALL EVENT =====

self.addEventListener('install', (event) => {
  console.warn('Service Worker installing...');

  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.warn('Caching essential files...');
        return cache.addAll(STATIC_FILES);
      })
      .then(() => {
        console.warn('Essential files cached');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('Cache installation failed:', error);
        return self.skipWaiting();
      }),
  );
});

// ===== ACTIVATE EVENT =====

self.addEventListener('activate', (event) => {
  console.warn('Service Worker activating...');

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => cacheName !== CACHE_NAME)
            .map((cacheName) => {
              console.warn('Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }),
        );
      })
      .then(() => {
        console.warn('Service Worker activated');
        return self.clients.claim();
      }),
  );
});

// ===== FETCH EVENT =====

self.addEventListener('fetch', (event) => {
  // Only handle GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  const { request } = event;
  const url = new URL(request.url);

  // Handle different types of requests
  if (isStaticAsset(url)) {
    event.respondWith(handleStaticAsset(request));
  } else if (isNavigationRequest(request)) {
    event.respondWith(handleNavigation(request));
  } else if (isAPIRequest(url)) {
    event.respondWith(handleAPI(request));
  }
});

// ===== MESSAGE HANDLING =====

self.addEventListener('message', (event) => {
  // Validate message origin to prevent unauthorized messages
  // Only accept messages from same origin
  if (event.origin !== self.location.origin) {
    console.warn('Service worker received message from unauthorized origin:', event.origin);
    return;
  }

  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// ===== ERROR HANDLING =====

self.addEventListener('error', (event) => {
  console.error('Service Worker error:', event.error);
});

self.addEventListener('unhandledrejection', (event) => {
  console.error('Service Worker unhandled rejection:', event.reason);
});

console.warn('Service Worker loaded successfully');
