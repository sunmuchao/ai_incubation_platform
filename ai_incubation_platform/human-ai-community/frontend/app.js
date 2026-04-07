/**
 * Human-AI Community - 前端应用
 * 版本：v0.6.0
 * 功能：完整的社区前端界面 MVP
 */

const API_BASE = 'http://localhost:8007';

// ==================== 全局状态 ====================
const AppState = {
  currentTab: 'home',
  currentUser: null,
  members: [],
  posts: [],
  channels: [],
  notifications: [],
  searchResults: null,
  loading: false
};

// ==================== 工具函数 ====================
function $(selector) {
  return document.querySelector(selector);
}

function $$(selector) {
  return document.querySelectorAll(selector);
}

// ==================== 触摸手势识别系统 ====================
const GestureHandler = {
  // 手势配置
  config: {
    swipeThreshold: 50,      // 滑动最小距离 (px)
    swipeVelocity: 0.3,      // 最小滑动速度
    tapMaxDuration: 200,     // 点击最大时长 (ms)
    longPressDuration: 500,  // 长按时长 (ms)
    doubleTapInterval: 300,  // 双击时间间隔 (ms)
    pinchThreshold: 10       // 捏合最小距离变化 (px)
  },

  // 手势状态
  state: {
    isTouching: false,
    startX: 0,
    startY: 0,
    lastTapTime: 0,
    longPressTimer: null,
    touchStartTime: 0,
    initialPinchDistance: null,
    lastTapTarget: null
  },

  // 初始化手势监听
  init() {
    if (this.isMobile()) {
      this.bindGlobalEvents();
      console.log('手势识别已初始化 (移动端)');
    }
  },

  // 判断是否为移动设备
  isMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
           window.innerWidth <= 768;
  },

  // 绑定全局事件
  bindGlobalEvents() {
    // 防止双击缩放
    document.addEventListener('dblclick', (e) => {
      if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
      }
    }, { passive: false });

    // 添加触摸反馈
    document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: true });
    document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: true });
  },

  handleTouchStart(e) {
    const touch = e.touches[0];
    this.state.isTouching = true;
    this.state.startX = touch.clientX;
    this.state.startY = touch.clientY;
    this.state.touchStartTime = Date.now();

    // 长按检测
    if (e.target.closest('[data-longpress]')) {
      this.state.longPressTimer = setTimeout(() => {
        this.triggerLongPress(e.target);
        this.state.isTouching = false;
      }, this.config.longPressDuration);
    }

    // 双指捏合检测
    if (e.touches.length === 2) {
      this.state.initialPinchDistance = this.getPinchDistance(e.touches);
    }
  },

  handleTouchEnd(e) {
    clearTimeout(this.state.longPressTimer);

    if (!this.state.isTouching) return;

    const touch = e.changedTouches[0];
    const deltaX = touch.clientX - this.state.startX;
    const deltaY = touch.clientY - this.state.startY;
    const duration = Date.now() - this.state.touchStartTime;
    const target = e.target;

    // 检测捏合手势
    if (this.state.initialPinchDistance && e.touches.length === 1) {
      // 捏合结束，已在 move 中处理
    }

    // 检测滑动手势
    if (Math.abs(deltaX) > this.config.swipeThreshold ||
        Math.abs(deltaY) > this.config.swipeThreshold) {
      this.handleSwipe(deltaX, deltaY, duration, target);
    }
    // 检测点击/双击
    else if (duration < this.config.tapMaxDuration) {
      this.handleTap(target);
    }

    this.state.isTouching = false;
    this.state.initialPinchDistance = null;
  },

  handleSwipe(deltaX, deltaY, duration, target) {
    const velocity = Math.sqrt(deltaX * deltaX + deltaY * deltaY) / duration;

    if (velocity < this.config.swipeVelocity) return;

    const absX = Math.abs(deltaX);
    const absY = Math.abs(deltaY);

    let direction;
    if (absX > absY) {
      direction = deltaX > 0 ? 'right' : 'left';
    } else {
      direction = deltaY > 0 ? 'down' : 'up';
    }

    // 触发滑动事件
    const swipeEvent = new CustomEvent('swipe', {
      detail: { direction, deltaX, deltaY, velocity },
      bubbles: true
    });
    target.dispatchEvent(swipeEvent);

    // 全局滑动处理 - 用于标签切换
    if (target.closest('.panel') || target.closest('.main-content')) {
      this.handleGlobalSwipe(direction);
    }
  },

  handleGlobalSwipe(direction) {
    const currentTab = AppState.currentTab;
    const tabOrder = ['home', 'channels', 'search', 'notifications', 'profile', 'admin'];
    const currentIndex = tabOrder.indexOf(currentTab);

    // 左右滑动切换标签
    if (direction === 'left' && currentIndex < tabOrder.length - 1) {
      switchTab(tabOrder[currentIndex + 1]);
    } else if (direction === 'right' && currentIndex > 0) {
      switchTab(tabOrder[currentIndex - 1]);
    }

    // 下拉刷新
    if (direction === 'down' && currentTab === 'home' && window.scrollY < 50) {
      this.triggerPullToRefresh();
    }
  },

  handleTap(target) {
    const now = Date.now();
    const isDoubleTap = (now - this.state.lastTapTime) < this.config.doubleTapInterval &&
                        target === this.state.lastTapTarget;

    if (isDoubleTap) {
      // 双击事件
      const doubleTapEvent = new CustomEvent('doubletap', { bubbles: true });
      target.dispatchEvent(doubleTapEvent);

      // 帖子卡片双击点赞
      if (target.closest('.post-card')) {
        const postCard = target.closest('.post-card');
        const postId = postCard.dataset.postId;
        this.handleDoubleTapPost(postId, postCard);
      }
    }

    this.state.lastTapTime = now;
    this.state.lastTapTarget = target;
  },

  handleDoubleTapPost(postId, postCard) {
    // 显示点赞动画
    const likeAnimation = document.createElement('span');
    likeAnimation.className = 'double-tap-like';
    likeAnimation.innerHTML = '👍';
    likeAnimation.style.cssText = `
      position: absolute;
      font-size: 3rem;
      animation: likePop 0.6s ease-out forwards;
      pointer-events: none;
      z-index: 100;
    `;
    postCard.style.position = 'relative';
    postCard.appendChild(likeAnimation);

    setTimeout(() => likeAnimation.remove(), 600);

    // 这里可以调用点赞 API
    showToast('已点赞', 'success');
  },

  triggerPullToRefresh() {
    const refreshEvent = new CustomEvent('pulltorefresh', { bubbles: true });
    document.dispatchEvent(refreshEvent);
  },

  getPinchDistance(touches) {
    const dx = touches[0].clientX - touches[1].clientX;
    const dy = touches[0].clientY - touches[1].clientY;
    return Math.sqrt(dx * dx + dy * dy);
  },

  triggerLongPress(target) {
    const longPressEvent = new CustomEvent('longpress', {
      detail: { target },
      bubbles: true
    });
    target.dispatchEvent(longPressEvent);
  }
};

// 添加双击点赞动画样式
const style = document.createElement('style');
style.textContent = `
  @keyframes likePop {
    0% {
      transform: scale(0) rotate(-15deg);
      opacity: 0;
    }
    50% {
      transform: scale(1.5) rotate(0deg);
      opacity: 1;
    }
    100% {
      transform: scale(1) rotate(15deg);
      opacity: 0;
    }
  }
  .double-tap-like {
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
  }
`;
document.head.appendChild(style);

function showLoading(elementId, show = true) {
  const el = $(elementId);
  if (el) {
    el.innerHTML = show ? '<span class="loading"></span> 加载中...' : '';
  }
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

async function apiCall(endpoint, method = 'GET', body = null) {
  const options = {
    method,
    headers: { 'Content-Type': 'application/json' }
  };
  if (body) options.body = JSON.stringify(body);

  const response = await fetch(`${API_BASE}${endpoint}`, options);
  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `HTTP ${response.status}`);
  }
  return response.json();
}

function formatDate(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  const now = new Date();
  const diff = now - date;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  if (days < 7) return `${days}天前`;
  return date.toLocaleDateString('zh-CN');
}

function formatNumber(num) {
  if (num >= 10000) return `${(num / 10000).toFixed(1)}万`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
  return num.toString();
}

// ==================== 导航与标签页 ====================
function initTabs() {
  $$('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      $$('.tab-btn').forEach(b => b.classList.remove('active'));
      $$('.panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      $(`#panel-${btn.dataset.tab}`).classList.add('active');
      AppState.currentTab = btn.dataset.tab;

      // 加载对应数据
      loadTabData(btn.dataset.tab);
    });
  });
}

async function loadTabData(tab) {
  switch(tab) {
    case 'home':
      await loadHomeFeed('hot');
      break;
    case 'channels':
      await loadChannels();
      break;
    case 'search':
      // 搜索页不自动加载
      break;
    case 'notifications':
      await loadNotifications();
      break;
    case 'profile':
      await loadProfile();
      break;
    case 'admin':
      await loadAdminPanel();
      break;
  }
}

// ==================== 首页信息流 ====================
async function loadHomeFeed(sort = 'hot') {
  showLoading('feed-loading', true);
  try {
    let endpoint = '/api/posts?sort=' + sort;
    const posts = await apiCall(endpoint);
    AppState.posts = posts;
    renderFeed(posts, sort);
  } catch (e) {
    console.error('加载信息流失败:', e);
    showToast('加载失败：' + e.message, 'error');
  } finally {
    showLoading('feed-loading', false);
  }
}

function renderFeed(posts, sort) {
  const container = $('#feed-list');
  const bentoContainer = $('#feed-bento-grid');

  if (!posts || posts.length === 0) {
    container.innerHTML = '<div class="empty-state"><p>暂无内容，快来发布第一个帖子吧！</p></div>';
    if (bentoContainer) bentoContainer.innerHTML = '';
    return;
  }

  // Bento Grid 布局渲染
  if (bentoContainer) {
    bentoContainer.innerHTML = posts.slice(0, 8).map((post, index) => {
      // 根据索引决定 Bento 卡片尺寸
      let sizeClass = 'bento-sm';
      if (index === 0) sizeClass = 'bento-lg';  // 第一个帖子是大卡片
      else if (index <= 2) sizeClass = 'bento-md';  // 前三个是中等卡片

      const isHot = post.heat_score && post.heat_score > 100;

      return `
        <div class="bento-card ${sizeClass} ${isHot ? 'glow-effect' : ''}" data-post-id="${post.id}" onclick="viewPost(${post.id})">
          <div class="bento-card-header">
            <span class="bento-card-title">${isHot ? '🔥 热门' : '帖子'}</span>
            <div class="bento-card-icon">${post.channel_name ? '📁' : '💬'}</div>
          </div>
          <div class="post-header" style="margin-bottom: var(--space-2);">
            <div class="post-meta">
              <span class="author-badge ${post.author_type === 'ai' ? 'ai' : 'human'}">
                ${post.author_type === 'ai' ? 'AI' : '人类'}
              </span>
              <span class="author-name">${post.author_name || `用户${post.author_id}`}</span>
              <span class="post-time">${formatDate(post.created_at)}</span>
            </div>
          </div>
          <h3 class="post-title" style="font-size: 1rem; margin-bottom: var(--space-2);">${escapeHtml(post.title)}</h3>
          <div class="post-content" style="font-size: 0.875rem; margin-bottom: var(--space-3);">${escapeHtml(post.content).substring(0, 150)}${post.content.length > 150 ? '...' : ''}</div>
          <div class="post-stats" style="display: flex; gap: var(--space-3); font-size: 0.75rem; color: var(--text-tertiary);">
            <span class="stat-item"><span class="stat-icon">👍</span> ${formatNumber(post.upvotes || 0)}</span>
            <span class="stat-item"><span class="stat-icon">💬</span> ${formatNumber(post.comment_count || 0)}</span>
            ${post.heat_score ? `<span class="stat-item heat">🔥 ${formatNumber(post.heat_score)}</span>` : ''}
          </div>
        </div>
      `;
    }).join('');
  }

  // 传统列表视图渲染
  container.innerHTML = posts.map(post => `
    <div class="post-card" data-post-id="${post.id}" onclick="viewPost(${post.id})">
      <div class="post-header">
        <div class="post-meta">
          <span class="author-badge ${post.author_type === 'ai' ? 'ai' : 'human'}">
            ${post.author_type === 'ai' ? 'AI' : '人类'}
          </span>
          <span class="author-name">${post.author_name || `用户${post.author_id}`}</span>
          <span class="post-time">${formatDate(post.created_at)}</span>
        </div>
        ${post.channel_name ? `<span class="channel-tag">${post.channel_name}</span>` : ''}
      </div>
      <h3 class="post-title">${escapeHtml(post.title)}</h3>
      <div class="post-content">${escapeHtml(post.content).substring(0, 300)}${post.content.length > 300 ? '...' : ''}</div>
      <div class="post-footer">
        <div class="post-stats">
          <span class="stat-item"><span class="stat-icon">👍</span> ${formatNumber(post.upvotes || 0)}</span>
          <span class="stat-item"><span class="stat-icon">💬</span> ${formatNumber(post.comment_count || 0)}</span>
          <span class="stat-item"><span class="stat-icon">👁</span> ${formatNumber(post.views || 0)}</span>
          ${post.heat_score ? `<span class="stat-item heat">🔥 ${formatNumber(post.heat_score)}</span>` : ''}
        </div>
        <div class="post-actions">
          <button class="action-btn" onclick="event.stopPropagation(); viewPost(${post.id})">查看详情</button>
          <button class="action-btn" onclick="event.stopPropagation(); toggleBookmark(${post.id})">收藏</button>
        </div>
      </div>
    </div>
  `).join('');
}

// ==================== 频道系统 ====================
async function loadChannels() {
  showLoading('channels-loading', true);
  try {
    const channels = await apiCall('/api/channels');
    AppState.channels = channels;
    renderChannels(channels);
  } catch (e) {
    console.error('加载频道失败:', e);
    showToast('加载失败：' + e.message, 'error');
  } finally {
    showLoading('channels-loading', false);
  }
}

function renderChannels(channels) {
  const container = $('#channels-list');
  if (!channels || channels.length === 0) {
    container.innerHTML = '<div class="empty-state"><p>暂无频道</p></div>';
    return;
  }

  // 按分类分组
  const byCategory = {};
  channels.forEach(ch => {
    const catName = ch.category_name || '未分类';
    if (!byCategory[catName]) byCategory[catName] = [];
    byCategory[catName].push(ch);
  });

  let html = '';
  for (const [catName, chs] of Object.entries(byCategory)) {
    html += `
      <div class="channel-category">
        <h3 class="category-title">${escapeHtml(catName)}</h3>
        <div class="channel-grid">
          ${chs.map(ch => `
            <div class="channel-card" onclick="viewChannel(${ch.id})">
              <div class="channel-icon">${ch.icon || '📁'}</div>
              <div class="channel-info">
                <h4 class="channel-name">${escapeHtml(ch.name)}</h4>
                <p class="channel-desc">${escapeHtml(ch.description || '')}</p>
                <div class="channel-stats">
                  <span>${ch.member_count || 0} 成员</span>
                  <span>${ch.post_count || 0} 帖子</span>
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }
  container.innerHTML = html;
}

async function createChannel() {
  const name = $('#new-channel-name').value;
  const description = $('#new-channel-desc').value;
  const categoryId = $('#new-channel-category').value;

  if (!name) {
    showToast('请输入频道名称', 'error');
    return;
  }

  try {
    await apiCall('/api/channels', 'POST', {
      name,
      description,
      category_id: parseInt(categoryId) || null
    });
    showToast('频道创建成功', 'success');
    $('#channel-modal').classList.remove('active');
    await loadChannels();
  } catch (e) {
    showToast('创建失败：' + e.message, 'error');
  }
}

// ==================== 搜索功能 ====================
async function performSearch() {
  const query = $('#search-input').value.trim();
  const type = $('#search-type').value;
  const channel = $('#search-channel').value;

  if (!query) {
    showToast('请输入搜索关键词', 'error');
    return;
  }

  showLoading('search-loading', true);
  try {
    let endpoint = `/api/search/${type}?q=${encodeURIComponent(query)}`;
    if (channel) endpoint += `&channel_id=${channel}`;

    const results = await apiCall(endpoint);
    AppState.searchResults = results;
    renderSearchResults(results, type);
  } catch (e) {
    console.error('搜索失败:', e);
    showToast('搜索失败：' + e.message, 'error');
  } finally {
    showLoading('search-loading', false);
  }
}

function renderSearchResults(results, type) {
  const container = $('#search-results');
  const items = type === 'all' ? results.all : (results || []);

  if (!items || items.length === 0) {
    container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔍</div><p>未找到相关内容</p></div>';
    return;
  }

  container.innerHTML = items.map(item => `
    <div class="search-result-item" style="padding: var(--space-4); background: var(--bg-secondary); border: 1px solid var(--border-default); border-radius: var(--radius-lg); margin-bottom: var(--space-3); transition: all var(--duration-fast);">
      <h4 style="font-size: 0.9375rem; font-weight: 600; color: var(--text-primary); margin-bottom: var(--space-2);">${highlightMatch(escapeHtml(item.title || item.content), AppState.searchQuery)}</h4>
      <div class="search-result-meta" style="display: flex; gap: var(--space-2); font-size: 0.75rem; color: var(--text-tertiary);">
        <span class="result-type" style="background: var(--bg-tertiary); padding: 1px 6px; border-radius: var(--radius-sm);">${type === 'comments' ? '评论' : '帖子'}</span>
        <span class="result-author">${item.author_name || `用户${item.author_id}`}</span>
        <span class="result-time">${formatDate(item.created_at)}</span>
      </div>
    </div>
  `).join('');
}

function highlightMatch(text, query) {
  if (!query) return text;
  const regex = new RegExp(`(${escapeRegExp(query)})`, 'gi');
  return text.replace(regex, '<mark>$1</mark>');
}

function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ==================== 通知中心 ====================
async function loadNotifications() {
  try {
    const notifications = await apiCall('/api/notifications?limit=50');
    AppState.notifications = notifications;
    renderNotifications(notifications);
  } catch (e) {
    console.error('加载通知失败:', e);
  }
}

function renderNotifications(notifications) {
  const container = $('#notifications-list');
  if (!notifications || notifications.length === 0) {
    container.innerHTML = '<div class="empty-state"><p>暂无通知</p></div>';
    return;
  }

  container.innerHTML = notifications.map(n => `
    <div class="notification-item ${n.is_read ? 'read' : 'unread'}" data-notif-id="${n.id}">
      <div class="notif-icon">${getNotifIcon(n.type)}</div>
      <div class="notif-content">
        <div class="notif-text">${escapeHtml(n.content)}</div>
        <div class="notif-meta">
          <span class="notif-time">${formatDate(n.created_at)}</span>
          ${!n.is_read ? '<button class="mark-read-btn" onclick="markAsRead(' + n.id + ')">标记已读</button>' : ''}
        </div>
      </div>
    </div>
  `).join('');
}

function getNotifIcon(type) {
  const icons = {
    'system': '🔔',
    'approval': '✅',
    'rejection': '❌',
    'warning': '⚠️',
    'reply': '💬',
    'mention': '@',
    'like': '👍',
    'bookmark': '⭐'
  };
  return icons[type] || '📬';
}

async function markAsRead(notificationId) {
  try {
    await apiCall(`/api/notifications/${notificationId}/read`, 'PUT');
    $(`[data-notif-id="${notificationId}"]`).classList.add('read');
  } catch (e) {
    showToast('操作失败', 'error');
  }
}

async function markAllAsRead() {
  try {
    await apiCall('/api/notifications/read-all', 'PUT');
    await loadNotifications();
    showToast('已全部标记为已读', 'success');
  } catch (e) {
    showToast('操作失败', 'error');
  }
}

// ==================== 个人中心 ====================
async function loadProfile() {
  // 加载用户信息
  try {
    const members = await apiCall('/api/members');
    AppState.members = members;

    // 加载等级信息
    const levels = await apiCall('/api/levels/config');

    renderProfile(members, levels);
  } catch (e) {
    console.error('加载个人中心失败:', e);
  }
}

function renderProfile(members, levels) {
  const container = $('#profile-content');

  // 显示所有成员列表（演示用）
  container.innerHTML = `
    <div class="profile-section">
      <h3>成员列表</h3>
      <div class="members-grid">
        ${members.map(m => `
          <div class="member-card">
            <div class="member-avatar">${(m.username || m.name || 'U')[0].toUpperCase()}</div>
            <div class="member-info">
              <h4>${escapeHtml(m.username || m.name || '未知用户')}</h4>
              <span class="member-type ${m.member_type === 'ai' ? 'ai' : 'human'}">
                ${m.member_type === 'ai' ? 'AI 成员' : '人类成员'}
              </span>
            </div>
          </div>
        `).join('')}
      </div>
    </div>

    <div class="profile-section">
      <h3>等级体系说明</h3>
      <div class="level-info">
        <p>当前等级体系共 18 级，通过发帖、评论、签到等方式获取经验值升级。</p>
        <div class="level-grid">
          ${levels?.levels?.map(l => `
            <div class="level-item">
              <span class="level-badge">Lv.${l.level}</span>
              <span class="level-name">${l.name}</span>
              <span class="level-exp">${l.min_experience}+ 经验</span>
            </div>
          `).join('') || '<p>等级信息加载中...</p>'}
        </div>
      </div>
    </div>
  `;
}

// ==================== 管理后台 ====================
async function loadAdminPanel() {
  try {
    // 加载审核队列
    const queue = await apiCall('/api/moderation/queue');
    // 加载治理统计
    const stats = await apiCall('/api/governance/stats');

    renderAdminPanel(queue, stats);
  } catch (e) {
    console.error('加载管理后台失败:', e);
  }
}

function renderAdminPanel(queue, stats) {
  const container = $('#admin-content');

  container.innerHTML = `
    <div class="admin-section">
      <h3>治理统计</h3>
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">${stats.total_users || 0}</div>
          <div class="stat-label">总用户数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${stats.total_posts || 0}</div>
          <div class="stat-label">总帖子数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${stats.pending_reviews || 0}</div>
          <div class="stat-label">待审核</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${stats.auto_approval_rate || 0}%</div>
          <div class="stat-label">自动审核率</div>
        </div>
      </div>
    </div>

    <div class="admin-section">
      <h3>待审核队列</h3>
      ${queue.length > 0 ? `
        <div class="review-queue">
          ${queue.map(item => `
            <div class="review-item">
              <div class="review-info">
                <span class="content-type">${item.content_type}</span>
                <span class="review-reason">${item.reason || '待审核'}</span>
              </div>
              <div class="review-actions">
                <button class="btn-approve" onclick="approveContent('${item.content_type}', ${item.content_id})">通过</button>
                <button class="btn-reject" onclick="rejectContent('${item.content_type}', ${item.content_id})">拒绝</button>
              </div>
            </div>
          `).join('')}
        </div>
      ` : '<div class="empty-state"><p>暂无待审核内容</p></div>'}
    </div>
  `;
}

async function approveContent(contentType, contentId) {
  try {
    await apiCall('/api/moderation/approve', 'POST', {
      content_type: contentType,
      content_id: contentId
    });
    showToast('已通过', 'success');
    await loadAdminPanel();
  } catch (e) {
    showToast('操作失败：' + e.message, 'error');
  }
}

async function rejectContent(contentType, contentId) {
  try {
    await apiCall('/api/moderation/reject', 'POST', {
      content_type: contentType,
      content_id: contentId
    });
    showToast('已拒绝', 'success');
    await loadAdminPanel();
  } catch (e) {
    showToast('操作失败：' + e.message, 'error');
  }
}

// ==================== 帖子详情 ====================
async function viewPost(postId) {
  try {
    const post = await apiCall(`/api/posts/${postId}`);
    const comments = await apiCall(`/api/posts/${postId}/comments`) || [];

    showPostDetail(post, comments);
  } catch (e) {
    showToast('加载失败：' + e.message, 'error');
  }
}

function showPostDetail(post, comments) {
  const modal = $('#post-detail-modal');
  const content = $('#post-detail-content');

  content.innerHTML = `
    <div class="post-detail">
      <div class="post-detail-header">
        <h2>${escapeHtml(post.title)}</h2>
        <div class="post-meta">
          <span class="author-badge ${post.author_type === 'ai' ? 'ai' : 'human'}">
            ${post.author_type === 'ai' ? 'AI' : '人类'}
          </span>
          <span>${post.author_name || `用户${post.author_id}`}</span>
          <span>${formatDate(post.created_at)}</span>
        </div>
      </div>
      <div class="post-detail-content">${escapeHtml(post.content)}</div>
      <div class="post-detail-stats">
        <span>👍 ${post.upvotes || 0}</span>
        <span>💬 ${post.comment_count || 0}</span>
        <span>👁 ${post.views || 0}</span>
      </div>

      <div class="comments-section">
        <h3>评论 (${comments.length})</h3>
        <div class="comments-list">
          ${comments.map(c => `
            <div class="comment-item">
              <div class="comment-header">
                <span class="comment-author">${c.author_name || `用户${c.author_id}`}</span>
                <span class="comment-time">${formatDate(c.created_at)}</span>
              </div>
              <div class="comment-content">${escapeHtml(c.content)}</div>
            </div>
          `).join('')}
        </div>
      </div>
    </div>
  `;

  modal.classList.add('active');
}

// ==================== 发帖功能 ====================
async function submitPost() {
  const title = $('#new-post-title').value;
  const content = $('#new-post-content').value;
  const authorId = $('#new-post-author').value;
  const channelId = $('#new-post-channel').value;

  if (!title || !content) {
    showToast('请填写标题和内容', 'error');
    return;
  }

  try {
    const body = {
      title,
      content,
      author_id: parseInt(authorId) || 1
    };
    if (channelId) body.channel_id = parseInt(channelId);

    await apiCall('/api/posts', 'POST', body);
    showToast('发布成功', 'success');
    $('#post-modal').classList.remove('active');
    await loadHomeFeed('hot');
  } catch (e) {
    showToast('发布失败：' + e.message, 'error');
  }
}

// ==================== 工具函数 ====================
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// 全局函数暴露
window.viewPost = viewPost;
window.toggleBookmark = (id) => showToast('收藏功能开发中', 'info');
window.sharePost = (id) => showToast('分享功能开发中', 'info');
window.viewChannel = (id) => showToast('频道详情开发中', 'info');
window.markAsRead = markAsRead;
window.markAllAsRead = markAllAsRead;
window.performSearch = performSearch;
window.submitPost = submitPost;
window.createChannel = createChannel;
window.approveContent = approveContent;
window.rejectContent = rejectContent;
window.loadHomeFeed = loadHomeFeed;

// ==================== 国际化集成 ====================
/**
 * 切换语言
 * @param {string} lang - 语言代码
 */
async function changeLanguage(lang) {
  if (window.i18n) {
    await window.i18n.setLanguage(lang);
    showToast('语言已切换 / Language switched', 'success');
  }
}
window.changeLanguage = changeLanguage;

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
  initTabs();

  // 检查服务状态
  checkServiceStatus();

  // 加载默认内容
  loadHomeFeed('hot');
});

async function checkServiceStatus() {
  try {
    const health = await apiCall('/health');
    $('#status-indicator').classList.add('online');
    $('#status-text').textContent = '服务在线';
  } catch (e) {
    $('#status-indicator').classList.remove('online');
    $('#status-text').textContent = '服务离线';
  }
}

// ==================== PWA Service Worker 注册 ====================
const PWAHandler = {
  registration: null,
  updateAvailable: false,

  // 初始化
  async init() {
    if ('serviceWorker' in navigator) {
      try {
        this.registration = await navigator.serviceWorker.register('/sw.js', {
          scope: '/'
        });
        console.log('[PWA] Service Worker 注册成功:', this.registration.scope);

        // 监听更新
        this.registration.addEventListener('updatefound', () => {
          console.log('[PWA] 发现 Service Worker 更新');
          const newWorker = this.registration.installing;

          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              this.showUpdatePrompt();
            }
          });
        });

        // 监听推送通知
        this.setupPushNotifications();

        // 注册定期同步
        this.registerPeriodicSync();

      } catch (error) {
        console.error('[PWA] Service Worker 注册失败:', error);
      }
    } else {
      console.log('[PWA] Service Worker 不受支持');
    }

    // 初始化手势处理器
    GestureHandler.init();

    // 设置底部导航
    this.setupBottomNav();

    // 设置汉堡菜单
    this.setupHamburgerMenu();

    // 监听下拉刷新
    this.setupPullToRefresh();

    // 监听键盘快捷键
    this.setupKeyboardShortcuts();
  },

  // 显示更新提示
  showUpdatePrompt() {
    const toast = document.createElement('div');
    toast.className = 'toast toast-info';
    toast.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; gap: 1rem;">
        <span>新版本已准备就绪，刷新页面以更新</span>
        <button onclick="PWAHandler.refreshApp()" style="background: white; color: var(--accent-info); border: none; padding: 0.25rem 0.75rem; border-radius: 4px; cursor: pointer;">
          刷新
        </button>
      </div>
    `;
    document.body.appendChild(toast);
    this.updateAvailable = true;
  },

  // 刷新应用
  refreshApp() {
    if (this.registration && this.registration.waiting) {
      this.registration.waiting.postMessage({ type: 'SKIP_WAITING' });
    }
    window.location.reload();
  },

  // 设置推送通知
  async setupPushNotifications() {
    if (!('PushManager' in window)) {
      console.log('[PWA] 推送通知不受支持');
      return;
    }

    // 检查当前通知权限
    const permission = Notification.permission;
    console.log('[PWA] 通知权限:', permission);

    if (permission === 'granted') {
      this.subscribeToPush();
    } else if (permission !== 'denied') {
      // 可以在用户交互时请求权限
      window.requestNotificationPermission = () => this.requestPermission();
    }
  },

  // 请求通知权限
  async requestPermission() {
    try {
      const permission = await Notification.requestPermission();
      console.log('[PWA] 通知权限结果:', permission);

      if (permission === 'granted') {
        showToast('通知已启用', 'success');
        this.subscribeToPush();
      } else if (permission === 'denied') {
        showToast('通知已禁用，可在浏览器设置中重新启用', 'warning');
      }
    } catch (error) {
      console.error('[PWA] 请求通知权限失败:', error);
    }
  },

  // 订阅推送
  async subscribeToPush() {
    try {
      const subscription = await this.registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlBase64ToUint8Array('YOUR_VAPID_PUBLIC_KEY')
      });

      console.log('[PWA] 推送订阅成功:', subscription);

      // 将订阅发送到服务器
      // await apiCall('/api/push/subscribe', 'POST', subscription.toJSON());

    } catch (error) {
      console.error('[PWA] 推送订阅失败:', error);
    }
  },

  // 注册定期同步
  async registerPeriodicSync() {
    if ('periodicSync' in window) {
      try {
        await navigator.periodicSync.register('refresh-content', {
          minInterval: 24 * 60 * 60 * 1000 // 24 小时
        });
        console.log('[PWA] 定期同步已注册');
      } catch (error) {
        console.error('[PWA] 定期同步注册失败:', error);
      }
    }
  },

  // 设置底部导航
  setupBottomNav() {
    // 检查是否需要显示底部导航（移动端）
    if (window.innerWidth <= 768) {
      this.ensureBottomNav();
    }

    window.addEventListener('resize', () => {
      if (window.innerWidth <= 768) {
        this.ensureBottomNav();
      } else {
        const existingNav = document.querySelector('.bottom-nav');
        if (existingNav) existingNav.remove();
      }
    });
  },

  // 确保底部导航存在
  ensureBottomNav() {
    if (document.querySelector('.bottom-nav')) return;

    const bottomNav = document.createElement('nav');
    bottomNav.className = 'bottom-nav';
    bottomNav.innerHTML = `
      <ul class="bottom-nav-menu">
        <li class="bottom-nav-item" data-tab="home">
          <span class="bottom-nav-icon">🏠</span>
          <span>首页</span>
        </li>
        <li class="bottom-nav-item" data-tab="channels">
          <span class="bottom-nav-icon">📁</span>
          <span>频道</span>
        </li>
        <li class="bottom-nav-item" data-tab="search">
          <span class="bottom-nav-icon">🔍</span>
          <span>搜索</span>
        </li>
        <li class="bottom-nav-item" data-tab="notifications">
          <span class="bottom-nav-icon">🔔</span>
          <span>通知</span>
        </li>
        <li class="bottom-nav-item" data-tab="profile">
          <span class="bottom-nav-icon">👤</span>
          <span>我的</span>
        </li>
      </ul>
    `;

    // 添加点击事件
    bottomNav.querySelectorAll('.bottom-nav-item').forEach(item => {
      item.addEventListener('click', () => {
        const tab = item.dataset.tab;
        bottomNav.querySelectorAll('.bottom-nav-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        switchTab(tab);
      });
    });

    document.body.appendChild(bottomNav);
    this.updateBottomNavActive(AppState.currentTab);
  },

  // 更新底部导航激活状态
  updateBottomNavActive(tab) {
    const bottomNav = document.querySelector('.bottom-nav');
    if (bottomNav) {
      bottomNav.querySelectorAll('.bottom-nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.tab === tab);
      });
    }
  },

  // 设置汉堡菜单
  setupHamburgerMenu() {
    // 检查是否需要汉堡菜单
    if (window.innerWidth <= 768) {
      this.ensureHamburgerMenu();
    }

    window.addEventListener('resize', () => {
      if (window.innerWidth <= 768) {
        this.ensureHamburgerMenu();
      } else {
        const menu = document.querySelector('.hamburger-menu');
        const drawer = document.querySelector('.mobile-nav-drawer');
        const overlay = document.querySelector('.mobile-nav-overlay');
        if (menu) menu.remove();
        if (drawer) drawer.remove();
        if (overlay) overlay.remove();
      }
    });
  },

  ensureHamburgerMenu() {
    if (document.querySelector('.hamburger-menu')) return;

    // 创建汉堡按钮
    const hamburger = document.createElement('button');
    hamburger.className = 'hamburger-menu';
    hamburger.innerHTML = '<span></span><span></span><span></span>';
    hamburger.addEventListener('click', () => this.toggleMobileDrawer());

    document.body.insertBefore(hamburger, document.body.firstChild);

    // 创建导航抽屉
    const drawer = document.createElement('div');
    drawer.className = 'mobile-nav-drawer';
    drawer.innerHTML = `
      <div class="mobile-nav-drawer-header">
        <h3 class="mobile-nav-drawer-title">Human-AI 社区</h3>
        <button class="mobile-nav-drawer-close">&times;</button>
      </div>
      <ul class="nav-menu">
        <li class="nav-item">
          <div class="nav-link" data-tab="home">
            <span class="nav-icon">🏠</span>
            <span>首页</span>
          </div>
        </li>
        <li class="nav-item">
          <div class="nav-link" data-tab="channels">
            <span class="nav-icon">📁</span>
            <span>频道</span>
          </div>
        </li>
        <li class="nav-item">
          <div class="nav-link" data-tab="search">
            <span class="nav-icon">🔍</span>
            <span>搜索</span>
          </div>
        </li>
        <li class="nav-item">
          <div class="nav-link" data-tab="notifications">
            <span class="nav-icon">🔔</span>
            <span>通知</span>
          </div>
        </li>
        <li class="nav-item">
          <div class="nav-link" data-tab="profile">
            <span class="nav-icon">👤</span>
            <span>个人中心</span>
          </div>
        </li>
        <li class="nav-item">
          <div class="nav-link" data-tab="admin">
            <span class="nav-icon">⚙️</span>
            <span>管理后台</span>
          </div>
        </li>
      </ul>
    `;

    // 关闭按钮事件
    drawer.querySelector('.mobile-nav-drawer-close').addEventListener('click', () => {
      this.closeMobileDrawer();
    });

    // 导航链接事件
    drawer.querySelectorAll('.nav-link').forEach(link => {
      link.addEventListener('click', () => {
        switchTab(link.dataset.tab);
        this.closeMobileDrawer();
      });
    });

    document.body.appendChild(drawer);

    // 创建遮罩层
    const overlay = document.createElement('div');
    overlay.className = 'mobile-nav-overlay';
    overlay.addEventListener('click', () => this.closeMobileDrawer());
    document.body.appendChild(overlay);
  },

  toggleMobileDrawer() {
    const drawer = document.querySelector('.mobile-nav-drawer');
    const overlay = document.querySelector('.mobile-nav-overlay');
    if (drawer && overlay) {
      drawer.classList.add('open');
      overlay.classList.add('open');
    }
  },

  closeMobileDrawer() {
    const drawer = document.querySelector('.mobile-nav-drawer');
    const overlay = document.querySelector('.mobile-nav-overlay');
    if (drawer && overlay) {
      drawer.classList.remove('open');
      overlay.classList.remove('open');
    }
  },

  // 设置下拉刷新
  setupPullToRefresh() {
    let startY = 0;
    let currentY = 0;
    let isPulling = false;

    document.addEventListener('touchstart', (e) => {
      if (window.scrollY === 0) {
        startY = e.touches[0].clientY;
        isPulling = true;
      }
    }, { passive: true });

    document.addEventListener('touchmove', (e) => {
      if (isPulling && window.scrollY === 0) {
        currentY = e.touches[0].clientY;
        const diff = currentY - startY;

        if (diff > 0 && diff < 150) {
          // 可以添加下拉视觉效果
        }
      }
    }, { passive: true });

    document.addEventListener('touchend', () => {
      if (isPulling) {
        const diff = currentY - startY;
        if (diff > 80) {
          // 触发下拉刷新
          loadHomeFeed('hot');
          showToast('正在刷新...', 'info');
        }
        isPulling = false;
        currentY = 0;
      }
    });
  },

  // 设置键盘快捷键
  setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Alt + 数字 切换标签
      if (e.altKey && e.key >= '1' && e.key <= '6') {
        e.preventDefault();
        const tabs = ['home', 'channels', 'search', 'notifications', 'profile', 'admin'];
        switchTab(tabs[parseInt(e.key) - 1]);
      }

      // Alt + N 请求通知权限
      if (e.altKey && (e.key === 'n' || e.key === 'N')) {
        e.preventDefault();
        if (window.requestNotificationPermission) {
          window.requestNotificationPermission();
        }
      }

      // Alt + R 刷新
      if (e.altKey && (e.key === 'r' || e.key === 'R')) {
        e.preventDefault();
        loadHomeFeed('hot');
        showToast('正在刷新...', 'info');
      }
    });
  },

  // VAPID key 转换工具
  urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }
};

// 注册全局更新函数
window.refreshApp = () => PWAHandler.refreshApp();

// 在 DOMContentLoaded 后初始化 PWA
document.addEventListener('DOMContentLoaded', () => {
  PWAHandler.init();
});
