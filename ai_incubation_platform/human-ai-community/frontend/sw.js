/**
 * Human-AI Community Service Worker
 * 版本：v1.18
 * 功能：离线缓存、推送通知、后台同步
 */

const CACHE_NAME = 'hai-community-v1.18';
const STATIC_CACHE = 'static-v1.18';
const DYNAMIC_CACHE = 'dynamic-v1.18';

// 静态资源缓存
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/styles.css',
  '/app.js',
  '/manifest.json'
];

// 动态缓存配置
const DYNAMIC_CACHE_CONFIG = {
  maxEntries: 50,
  maxAge: 7 * 24 * 60 * 60, // 7 天
  expireOnQuotaExhaustion: true
};

// API 缓存策略
const API_CACHE_STRATEGIES = {
  '/api/posts': { strategy: 'cacheFirst', maxAge: 5 * 60 }, // 5 分钟
  '/api/channels': { strategy: 'cacheFirst', maxAge: 10 * 60 }, // 10 分钟
  '/api/members': { strategy: 'cacheFirst', maxAge: 10 * 60 },
  '/api/notifications': { strategy: 'networkFirst', maxAge: 1 * 60 }, // 1 分钟
  '/api/levels': { strategy: 'cacheFirst', maxAge: 60 * 60 }, // 1 小时
};

// ==================== 安装事件 ====================
self.addEventListener('install', (event) => {
  console.log('[SW] Service Worker 安装中...');

  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] 缓存静态资源');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => {
        console.log('[SW] 静态资源缓存完成');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[SW] 缓存静态资源失败:', error);
      })
  );
});

// ==================== 激活事件 ====================
self.addEventListener('activate', (event) => {
  console.log('[SW] Service Worker 激活中...');

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => {
              return name.startsWith('static-') || name.startsWith('dynamic-');
            })
            .filter((name) => {
              return name !== STATIC_CACHE && name !== DYNAMIC_CACHE;
            })
            .map((name) => {
              console.log('[SW] 删除旧缓存:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => {
        console.log('[SW] Service Worker 激活完成');
        return self.clients.claim();
      })
  );
});

// ==================== 获取事件 ====================
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 只处理同源请求
  if (url.origin !== location.origin) {
    return;
  }

  // 判断请求类型
  if (request.method !== 'GET') {
    return;
  }

  // API 请求缓存策略
  if (url.pathname.startsWith('/api/')) {
    const apiPath = Object.keys(API_CACHE_STRATEGIES).find(
      path => url.pathname.startsWith(path)
    );

    if (apiPath) {
      const config = API_CACHE_STRATEGIES[apiPath];
      handleApiRequest(event, config);
      return;
    }

    // 默认 API 缓存策略
    handleApiRequest(event, { strategy: 'networkFirst', maxAge: 2 * 60 });
    return;
  }

  // 静态资源 - 缓存优先
  if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // HTML 页面 - 网络优先，离线时缓存
  if (request.mode === 'navigate' || url.pathname.endsWith('.html')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // 其他资源 - 缓存优先
  event.respondWith(cacheFirst(request, DYNAMIC_CACHE));
});

// ==================== 缓存策略实现 ====================

// 缓存优先策略
async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);

  if (cachedResponse) {
    console.log('[SW] 缓存命中:', request.url);

    // 后台更新缓存
    fetch(request).then((response) => {
      if (response && response.status === 200) {
        cache.put(request, response.clone());
      }
    }).catch(() => {
      // 网络失败，静默处理
    });

    return cachedResponse;
  }

  // 缓存未命中，从网络获取
  try {
    const response = await fetch(request);
    if (response && response.status === 200) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.error('[SW] 网络请求失败:', request.url, error);

    // 返回离线页面
    if (request.mode === 'navigate') {
      const offlinePage = await caches.match('/offline.html');
      return offlinePage || new Response('离线状态', {
        status: 503,
        statusText: 'Service Unavailable'
      });
    }

    throw error;
  }
}

// 网络优先策略
async function networkFirst(request) {
  try {
    const response = await fetch(request);

    if (response && response.status === 200) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    console.log('[SW] 网络失败，使用缓存:', request.url);

    const cache = await caches.open(DYNAMIC_CACHE);
    const cachedResponse = await cache.match(request);

    if (cachedResponse) {
      return cachedResponse;
    }

    // 返回离线页面
    if (request.mode === 'navigate') {
      const offlinePage = await caches.match('/offline.html');
      return offlinePage || new Response('离线状态', {
        status: 503,
        statusText: 'Service Unavailable'
      });
    }

    throw error;
  }
}

// API 请求处理
async function handleApiRequest(event, config) {
  const { request } = event;

  if (config.strategy === 'cacheFirst') {
    event.respondWith(cacheFirst(request, DYNAMIC_CACHE));
  } else {
    event.respondWith(networkFirst(request));
  }
}

// 判断是否为静态资源
function isStaticAsset(pathname) {
  const staticExtensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot'];
  return staticExtensions.some(ext => pathname.endsWith(ext));
}

// ==================== 推送通知 ====================
self.addEventListener('push', (event) => {
  console.log('[SW] 收到推送消息');

  let data = {};

  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data = { title: '新消息', body: event.data.text() };
    }
  }

  const title = data.title || 'Human-AI Community';
  const options = {
    body: data.body || '您有新的通知',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    image: data.image,
    data: data.url || '/',
    tag: data.tag || 'default',
    requireInteraction: data.requireInteraction || false,
    actions: data.actions || [
      { action: 'view', title: '查看' },
      { action: 'dismiss', title: '关闭' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// ==================== 通知点击 ====================
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] 通知被点击');

  event.notification.close();

  if (event.action === 'dismiss') {
    return;
  }

  const urlToOpen = event.notification.data || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((windowClients) => {
        // 检查是否有已打开的窗口
        for (let client of windowClients) {
          if (client.url === urlToOpen && 'focus' in client) {
            return client.focus();
          }
        }

        // 打开新窗口
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

// ==================== 后台同步 ====================
self.addEventListener('sync', (event) => {
  console.log('[SW] 后台同步触发:', event.tag);

  if (event.tag === 'sync-notifications') {
    event.waitUntil(syncNotifications());
  } else if (event.tag === 'sync-posts') {
    event.waitUntil(syncPosts());
  }
});

async function syncNotifications() {
  try {
    // 从服务器获取最新通知
    const response = await fetch('/api/notifications?limit=50');
    const notifications = await response.json();

    // 可以存储到 IndexedDB
    console.log('[SW] 同步通知完成:', notifications.length);
  } catch (error) {
    console.error('[SW] 同步通知失败:', error);
    throw error;
  }
}

async function syncPosts() {
  try {
    const response = await fetch('/api/posts?sort=hot');
    const posts = await response.json();
    console.log('[SW] 同步帖子完成:', posts.length);
  } catch (error) {
    console.error('[SW] 同步帖子失败:', error);
    throw error;
  }
}

// ==================== 消息处理 ====================
self.addEventListener('message', (event) => {
  console.log('[SW] 收到消息:', event.data);

  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'CLIENTS_CLAIM') {
    self.clients.claim();
  }

  if (event.data && event.data.type === 'CACHE_URLS') {
    event.waitUntil(
      caches.open(DYNAMIC_CACHE)
        .then((cache) => cache.addAll(event.data.urls))
    );
  }
});

// ==================== 定期后台任务 ====================
self.addEventListener('periodicsync', (event) => {
  console.log('[SW] 定期同步触发:', event.tag);

  if (event.tag === 'refresh-content') {
    event.waitUntil(refreshContent());
  }
});

async function refreshContent() {
  try {
    // 预取热门帖子
    await fetch('/api/posts?sort=hot');
    // 预取频道列表
    await fetch('/api/channels');
    console.log('[SW] 内容刷新完成');
  } catch (error) {
    console.error('[SW] 内容刷新失败:', error);
  }
}

console.log('[SW] Service Worker 已加载');
