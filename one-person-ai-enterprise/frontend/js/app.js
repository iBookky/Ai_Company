/* ═══════════════════════════════════════════════
   app.js — Core SPA Router + WebSocket + Utilities
   ═══════════════════════════════════════════════ */

const API = window.location.origin;
let ws = null;

let wsReconnectTimer = null;

// ─── Router ──────────────────────────────────────────────
// Use lazy function references to avoid "not defined" errors at parse time
const PAGES = {
  dashboard: { title: 'ภาพรวมระบบ',       subtitle: 'One-Person AI Enterprise',           onEnter: () => typeof loadDashboard !== 'undefined' && loadDashboard() },
  agents:    { title: 'จัดการ Agents',     subtitle: 'สร้างและแก้ไข AI Employees',          onEnter: () => typeof loadAgents !== 'undefined' && loadAgents() },
  skype:     { title: 'Telegram Rooms',    subtitle: 'ห้องบริหาร + ห้องปฏิบัติการ (Telegram Bot)', onEnter: () => typeof loadTelegram !== 'undefined' && loadTelegram() },
  logs:      { title: 'Logs & Monitoring', subtitle: 'ติดตาม Thought Process ของ Agents',  onEnter: () => typeof loadLogs !== 'undefined' && loadLogs() },
  drafts:    { title: 'Draft Repository',  subtitle: 'เอกสารร่างและการพิมพ์',              onEnter: () => typeof loadDrafts !== 'undefined' && loadDrafts() },
  settings:  { title: 'ตั้งค่าระบบ',      subtitle: 'API Keys, Telegram Bot, Models',     onEnter: () => typeof loadSettings !== 'undefined' && loadSettings() },

};

function navigateTo(page) {
  window.location.hash = `/${page}`;
}

function handleRoute() {
  const hash = window.location.hash.replace('#/', '') || 'dashboard';
  const page = hash.split('/')[0] || 'dashboard';

  // Hide all pages
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  // Show target page
  const pageEl = document.getElementById(`page-${page}`);
  const navEl = document.getElementById(`nav-${page}`);
  if (pageEl) pageEl.classList.add('active');
  if (navEl) navEl.classList.add('active');

  // Update title
  const config = PAGES[page] || PAGES.dashboard;
  document.getElementById('page-title').textContent = config.title;
  document.getElementById('page-subtitle').textContent = config.subtitle;

  // Focus & scroll scroll-container to top on page change
  const mainContent = document.getElementById('mainContent');
  if (mainContent) {
    mainContent.scrollTop = 0;
    mainContent.focus({ preventScroll: true });
  }

  // Run page loader
  if (config.onEnter) config.onEnter();
}


window.addEventListener('hashchange', handleRoute);
window.addEventListener('DOMContentLoaded', () => {
  handleRoute();
  initSidebar();
  initClock();
  initWebSocket();
  checkSystemHealth();
});

// ─── Sidebar Toggle ───────────────────────────────────────
function initSidebar() {
  document.getElementById('sidebarToggle').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('collapsed');
  });
}

// ─── Clock ────────────────────────────────────────────────
function initClock() {
  const el = document.getElementById('time-display');
  function tick() {
    const now = new Date();
    el.textContent = now.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
  tick();
  setInterval(tick, 1000);
}

// ─── WebSocket ────────────────────────────────────────────
function initWebSocket() {
  clearTimeout(wsReconnectTimer);
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${window.location.host}/api/logs/ws`;


  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setWsStatus('connected');
      // Ping every 30s
      setInterval(() => { if (ws && ws.readyState === WebSocket.OPEN) ws.send('ping'); }, 30000);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'pong') return;
        handleNewLog(data);
      } catch (e) { /* ignore */ }
    };

    ws.onerror = () => setWsStatus('error');

    ws.onclose = () => {
      setWsStatus('disconnected');
      wsReconnectTimer = setTimeout(initWebSocket, 5000);
    };
  } catch (e) {
    setWsStatus('error');
    wsReconnectTimer = setTimeout(initWebSocket, 5000);
  }
}

function setWsStatus(status) {
  const dot = document.querySelector('.ws-dot');
  const label = document.querySelector('.ws-label');
  if (!dot) return;
  dot.className = 'ws-dot';
  if (status === 'connected') {
    dot.classList.add('connected');
    label.textContent = 'Live';
  } else if (status === 'error') {
    dot.classList.add('error');
    label.textContent = 'Error';
  } else {
    label.textContent = 'Offline';
  }
}

// ─── System Health ────────────────────────────────────────
async function checkSystemHealth() {
  try {
    const res = await fetch(`${API}/api/health`);
    if (res.ok) {
      document.getElementById('status-dot').className = 'status-dot online';
      document.getElementById('status-text').textContent = 'ระบบออนไลน์';
    } else {
      setSystemError();
    }
  } catch (e) {
    setSystemError();
  }
}

function setSystemError() {
  document.getElementById('status-dot').className = 'status-dot error';
  document.getElementById('status-text').textContent = 'ระบบออฟไลน์';
}

// ─── Dashboard ────────────────────────────────────────────
async function loadDashboard() {
  await Promise.all([
    loadDashboardAgents(),
    loadDashboardLogs(),
    loadDashboardSkype(),
    loadDashboardStats(),
  ]);
}

async function loadDashboardStats() {
  try {
    const [agents, logs, drafts] = await Promise.all([
      apiFetch('/api/agents'),
      apiFetch('/api/logs?limit=200'),
      apiFetch('/api/drafts'),
    ]);
    document.getElementById('stat-agent-count').textContent = agents.length || 0;
    document.getElementById('stat-task-count').textContent = logs.length || 0;
    document.getElementById('stat-draft-count').textContent = drafts.length || 0;

    const errors = (logs || []).filter(l => l.level === 'ERROR');
    const errCount = errors.length;
    document.getElementById('stat-error-count').textContent = errCount;
    document.getElementById('agents-count').textContent = agents.length || 0;

    if (errCount > 0) {
      document.getElementById('error-count').textContent = errCount;
      document.getElementById('error-count').style.display = '';
    }
  } catch (e) { /* ignore */ }
}

async function loadDashboardAgents() {
  try {
    const agents = await apiFetch('/api/agents');
    const container = document.getElementById('dashboard-agents-list');
    if (!agents || !agents.length) {
      container.innerHTML = `<div class="empty-state"><span>🤖</span><p>ยังไม่มี Agent สร้างขึ้น</p></div>`;
      return;
    }
    container.innerHTML = agents.slice(0, 4).map(a => `
      <div class="agent-mini-item" onclick="navigateTo('agents')">
        <div class="agent-mini-icon">${agentEmoji(a.role)}</div>
        <div class="agent-mini-info">
          <div class="agent-mini-name">${esc(a.name)}</div>
          <div class="agent-mini-model">${esc(a.model)} • Temp: ${a.temperature}</div>
        </div>
      </div>
    `).join('');
  } catch (e) {
    document.getElementById('dashboard-agents-list').innerHTML = '<div class="empty-state"><p>โหลดไม่สำเร็จ</p></div>';
  }
}

async function loadDashboardLogs() {
  try {
    const logs = await apiFetch('/api/logs?limit=5');
    const container = document.getElementById('dashboard-log-feed');
    if (!logs || !logs.length) {
      container.innerHTML = `<div class="empty-state"><span>📋</span><p>ยังไม่มี log</p></div>`;
      return;
    }
    container.innerHTML = logs.map(l => `
      <div class="log-mini-item ${l.level}">
        <span>${levelIcon(l.level)}</span>
        <div>
          <div style="font-weight:500">${esc(l.agent_name)}</div>
          <div style="opacity:0.8">${esc(l.message)}</div>
        </div>
      </div>
    `).join('');
  } catch (e) { /* ignore */ }
}

async function loadDashboardSkype() {
  try {
    const rooms = await apiFetch('/api/telegram/rooms');
    const container = document.getElementById('skype-rooms-mini');
    if (!container) return;
    container.innerHTML = `
      <div class="room-mini">
        <div class="room-mini-name">🏛️ ห้องบริหารรวม (Admin)</div>
        <div class="room-config-status">
          ${rooms.admin_room?.configured
            ? '<span class="config-ok">✅ ตั้งค่าแล้ว</span>'
            : '<span class="config-no">❌ ยังไม่ตั้งค่า</span>'}
        </div>
        <div style="font-size:11px;color:var(--color-text-muted);margin-top:4px">
          ${rooms.admin_room?.id ? rooms.admin_room.id.substring(0,30) + '...' : 'ยังไม่มี Room ID'}
        </div>
      </div>
      <div class="room-mini">
        <div class="room-mini-name">⚙️ ห้องปฏิบัติการ</div>
        <div class="room-config-status">
          ${rooms.ops_room?.configured
            ? '<span class="config-ok">✅ ตั้งค่าแล้ว</span>'
            : '<span class="config-no">❌ ยังไม่ตั้งค่า</span>'}
        </div>
        <div style="font-size:11px;color:var(--color-text-muted);margin-top:4px">
          ${rooms.ops_room?.id ? rooms.ops_room.id.substring(0,30) + '...' : 'ยังไม่มี Room ID'}
        </div>
      </div>
    `;
  } catch (e) { /* ignore */ }
}

// ─── Real-time Log Handler ────────────────────────────────
function handleNewLog(logEntry) {
  // อัปเดต error count
  if (logEntry.level === 'ERROR') {
    const errEl = document.getElementById('error-count');
    const current = parseInt(errEl.textContent) || 0;
    errEl.textContent = current + 1;
    errEl.style.display = '';

    const statErr = document.getElementById('stat-error-count');
    statErr.textContent = parseInt(statErr.textContent || 0) + 1;
  }

  // เพิ่มลงใน logs table ถ้า page logs กำลังแสดง
  const logsPage = document.getElementById('page-logs');
  if (logsPage && logsPage.classList.contains('active')) {
    prependLogRow(logEntry);
  }

  // เพิ่มลงใน dashboard feed ถ้า page dashboard กำลังแสดง
  const dashFeed = document.getElementById('dashboard-log-feed');
  if (dashFeed) {
    const item = document.createElement('div');
    item.className = `log-mini-item ${logEntry.level}`;
    item.innerHTML = `<span>${levelIcon(logEntry.level)}</span>
      <div>
        <div style="font-weight:500">${esc(logEntry.agent_name)}</div>
        <div style="opacity:0.8">${esc(logEntry.message)}</div>
      </div>`;
    dashFeed.prepend(item);
    // จำกัดไว้ 5 รายการ
    while (dashFeed.children.length > 5) dashFeed.removeChild(dashFeed.lastChild);
  }
}

// ─── API Helper ───────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// ─── Toast ────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 3500) {
  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${icons[type] || ''}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'toastOut 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ─── Helpers ──────────────────────────────────────────────
function esc(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function levelIcon(level) {
  const icons = { ERROR: '🔴', WARNING: '🟡', SUCCESS: '🟢', INFO: '🔵', DEBUG: '⚪' };
  return icons[level] || '⚪';
}

function agentEmoji(role) {
  const map = {
    secretary: '🗂️',
    marketing_manager: '📢',
    marketing: '📢',
    pm: '📊',
    developer: '💻',
    agent: '🤖',
  };
  return map[role] || '🤖';
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleString('th-TH', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes/1024).toFixed(1)} KB`;
  return `${(bytes/(1024*1024)).toFixed(1)} MB`;
}

function fileIcon(contentType) {
  if (contentType?.includes('pdf')) return '📄';
  if (contentType?.includes('word') || contentType?.includes('document')) return '📝';
  if (contentType?.includes('excel') || contentType?.includes('spreadsheet')) return '📊';
  if (contentType?.includes('image')) return '🖼️';
  return '📎';
}
