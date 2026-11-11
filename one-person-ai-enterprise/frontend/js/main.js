/* ═══════════════════════════════════════════════════════════════
   main.js — One-Person AI Enterprise Frontend Logic
   ═══════════════════════════════════════════════════════════════ */

'use strict';

const API = '';  // same-origin

// ─── State ────────────────────────────────────────────────────
let allAgents   = [];
let allRooms    = {};
let allLogs     = [];
let wsLog       = null;
let sidebarOpen = true;
let _pendingProposal = null;

// ─── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  checkEnterpriseAuth();
  updateSidebarBadges();

  document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', (e) => {
      const page = el.dataset.page;
      if (page) {
        e.preventDefault();
        navigateTo(page);
      }
    });
  });

  routeFromHash();
  startClock();
  fetchHealthCheck();
  connectLogWS();
  initCompanyShift();

  window.addEventListener('hashchange', () => {
    routeFromHash();
    updateSidebarBadges();
  });
  window.addEventListener('resize', () => {
    if (window.innerWidth < 780) collapseSidebar();
  });
});

async function updateSidebarBadges() {
  try {
    const agents = await apiGet('/api/agents').catch(() => []);
    const deptCount = new Set((agents || []).map(a => a.department)).size;
    const badgeTeams = document.getElementById('badge-teams');
    if (badgeTeams) badgeTeams.textContent = deptCount;
    const badgeWorkstations = document.getElementById('badge-workstations');
    if (badgeWorkstations) badgeWorkstations.textContent = (agents || []).length;
    const statTeamCount = document.getElementById('stat-ai-team-count');
    if (statTeamCount) statTeamCount.textContent = (agents || []).length;
  } catch (err) {
    console.warn('Failed to update sidebar badges:', err);
  }
}

// ─── Routing ──────────────────────────────────────────────────
const PAGES = {
  dashboard: {
    title: 'บอร์ดสั่งการ (Visual Kanban)',
    sub: 'One-Person AI Enterprise Command Center — สั่งงาน ติดตาม และอนุมัติปิดงาน (HITL)',
    load: () => {
      loadDashboard();
      if (typeof fetchSimulationState === 'function') fetchSimulationState();
    }
  },
  workstations: {
    title: 'โต๊ะทำงานพนักงาน AI (Virtual Cockpit)',
    sub: 'ติดตามสถานะการทำงานสด, Task งาน, และประวัติผลงานย้อนหลังของพนักงาน AI แต่ละคน',
    load: () => { if (typeof loadWorkstations === 'function') loadWorkstations(); }
  },
  boardroom: { title: 'ห้องประชุมผู้บริหาร', sub: 'กำหนดนโยบาย สั่งงาน ประชุม Director', load: loadBoardroom },
  simulation: {
    title: 'บอร์ดสั่งการ (Visual Kanban)',
    sub: 'One-Person AI Enterprise Command Center',
    load: () => { navigateTo('dashboard'); }
  },
  kanban: {
    title: 'บอร์ดสั่งการ (Visual Kanban)',
    sub: 'One-Person AI Enterprise Command Center',
    load: () => { navigateTo('dashboard'); }
  },
  teams:      { title: 'ทีมปฏิบัติการ AI', sub: 'จัดการโครงสร้างทีมและพนักงาน AI', load: loadTeams },
  directives: { title: 'ทิศทาง & นโยบายบริษัท', sub: 'กำหนดเวลาทำงาน ทิศทางองค์กร นโยบายความปลอดภัย และรูปแบบบริษัท', load: loadDirectivesPage },
  logs:       { title: 'Logs การทำงาน', sub: 'ติดตาม Log ระบบ Real-time', load: loadLogs },
  settings:   { title: 'ตั้งค่าระบบ', sub: 'API Keys, Bot Token, ความปลอดภัย, การเชื่อมต่อ', load: loadSettings },
};

function routeFromHash() {
  const raw = location.hash.replace('#/', '') || 'dashboard';
  const pagePart = raw.split('?')[0].split('/')[0];
  const page = PAGES[pagePart] ? pagePart : 'dashboard';
  activatePage(page);
}

function navigateTo(page) {
  if (location.hash === '#/' + page) {
    activatePage(page);
  } else {
    location.hash = '#/' + page;
  }
}

function activatePage(page) {
  const cfg = PAGES[page];
  if (!cfg) return;

  // Update topbar
  document.getElementById('page-title').textContent = cfg.title;
  document.getElementById('page-subtitle').textContent = cfg.sub;

  // Update nav
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });

  // Show/hide pages
  document.querySelectorAll('.page').forEach(el => el.classList.remove('active'));
  document.getElementById('page-' + page)?.classList.add('active');

  cfg.load();
}

// ─── Sidebar ──────────────────────────────────────────────────
function toggleSidebar() {
  sidebarOpen = !sidebarOpen;
  const sidebar = document.getElementById('sidebar');
  const btn = document.getElementById('sidebar-toggle');
  sidebar.classList.toggle('collapsed', !sidebarOpen);
  btn.textContent = sidebarOpen ? '‹' : '›';
}
function collapseSidebar() {
  sidebarOpen = false;
  document.getElementById('sidebar').classList.add('collapsed');
  document.getElementById('sidebar-toggle').textContent = '›';
}

// ─── Clock ────────────────────────────────────────────────────
function startClock() {
  const update = () => {
    const now = new Date();
    const fmt  = now.toLocaleTimeString('th-TH', { timeZone: 'Asia/Bangkok', hour12: false });
    const date = now.toLocaleDateString('th-TH', { timeZone: 'Asia/Bangkok', weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
    document.getElementById('topbar-time').textContent = fmt;
    document.getElementById('sys-time').textContent = date;
  };
  update();
  setInterval(update, 1000);
}

// ─── Health Check ─────────────────────────────────────────────
async function fetchHealthCheck() {
  try {
    const r = await fetch(`${API}/api/health`);
    if (r.ok) {
      document.getElementById('status-dot').className  = 'status-dot online';
      document.getElementById('status-text').textContent = 'ระบบออนไลน์';
      document.getElementById('live-badge').style.display = '';
    }
  } catch {
    document.getElementById('status-dot').className  = 'status-dot offline';
    document.getElementById('status-text').textContent = 'ออฟไลน์';
    document.getElementById('live-badge').style.display = 'none';
  }
}

// ─── Fetch Helpers ────────────────────────────────────────────
async function apiGet(path) {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
async function apiPost(path, body) {
  const r = await fetch(`${API}${path}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
async function apiPut(path, body) {
  const r = await fetch(`${API}${path}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
async function apiPatch(path, body) {
  const r = await fetch(`${API}${path}`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
async function apiDelete(path) {
  const r = await fetch(`${API}${path}`, { method: 'DELETE' });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

// ─── Toast ────────────────────────────────────────────────────
function toast(msg, type = 'info', duration = 3500) {
  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${msg}</span>`;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => { el.classList.add('fade-out'); setTimeout(() => el.remove(), 350); }, duration);
}

// ─── Modal ────────────────────────────────────────────────────
function openModal(id) { document.getElementById(id)?.classList.add('open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }

// ─── WebSocket Log Stream ─────────────────────────────────────
function connectLogWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const wsUrl = `${proto}://${location.host}/api/logs/ws`;

  wsLog = new WebSocket(wsUrl);

  wsLog.onopen = () => {
    console.log('[WS] Log stream connected');
  };

  wsLog.onmessage = (e) => {
    try {
      const entry = JSON.parse(e.data);
      if (entry.type === 'pong') return;
      allLogs.unshift(entry);
      if (allLogs.length > 500) allLogs = allLogs.slice(0, 500);

      // Update dashboard mini log
      updateDashboardLogPreview();

      // Update badge
      const errors = allLogs.filter(l => l.level === 'ERROR').length;
      const badge = document.getElementById('badge-errors');
      if (errors > 0) {
        badge.style.display = '';
        badge.textContent = errors;
      }

      // If on logs page, add to stream
      if (document.getElementById('page-logs').classList.contains('active')) {
        prependLogEntry(entry);
      }
    } catch {}
  };

  wsLog.onclose = () => {
    setTimeout(() => connectLogWS(), 3000);
  };

  // Heartbeat
  setInterval(() => { if (wsLog && wsLog.readyState === WebSocket.OPEN) wsLog.send('ping'); }, 25000);
}

// ══════════════════════════════════════════════════════════════
//  PAGE: DASHBOARD (Visual Kanban & Stats)
// ══════════════════════════════════════════════════════════════
async function loadDashboard() {
  try {
    const [agents, rooms] = await Promise.all([
      apiGet('/api/agents').catch(() => []),
      apiGet('/api/telegram/rooms').catch(() => ({})),
    ]);
    allAgents = agents || [];
    allRooms  = rooms || {};

    // Stats
    const depts = new Set((agents || []).map(a => a.department)).size;
    const statAgents = document.getElementById('stat-agents');
    if (statAgents) statAgents.textContent = (agents || []).length;
    const statDepts = document.getElementById('stat-depts');
    if (statDepts) statDepts.textContent = depts;
    const statLogs = document.getElementById('stat-logs');
    if (statLogs) statLogs.textContent = allLogs.length;
    const statTg = document.getElementById('stat-telegram');
    if (statTg) statTg.textContent = rooms?.bot_configured ? '✓ เชื่อมต่อ' : '✗ ยังไม่ตั้งค่า';
    const badgeTeams = document.getElementById('badge-teams');
    if (badgeTeams) badgeTeams.textContent = depts;
    const badgeWorkstations = document.getElementById('badge-workstations');
    if (badgeWorkstations) badgeWorkstations.textContent = (agents || []).length;

    // Quick teams
    renderQuickTeams(rooms || {});

    // Log preview
    updateDashboardLogPreview();
    
    // Load Model Usage Stats
    if (typeof loadUsageStats === 'function') loadUsageStats();

    // Fetch and render Kanban Simulation state
    if (typeof fetchSimulationState === 'function') {
      fetchSimulationState();
    }
  } catch (err) {
    console.warn('Dashboard load warning:', err);
  }
}

function renderQuickTeams(rooms) {
  const el = document.getElementById('quick-teams-list');
  const depts = rooms.department_rooms || {};
  const keys = Object.keys(depts);
  if (keys.length === 0) {
    el.innerHTML = `<div class="empty-state"><div>ยังไม่มีทีม</div><button class="btn btn-sm btn-primary" onclick="navigateTo('teams')">＋ สร้างทีมแรก</button></div>`;
    return;
  }
  el.innerHTML = keys.map(id => {
    const d = depts[id];
    return `
      <div class="quick-team-row">
        <span class="quick-team-name">🏢 ${d.name}</span>
        <span class="quick-team-pm">${d.pm_name || '—'}</span>
        <button class="btn btn-sm btn-primary" onclick="openDirectCommandModal('${id}', '${escHtml(d.name)}')">💬 สั่งงาน</button>
      </div>`;
  }).join('');
}

function updateDashboardLogPreview() {
  const el = document.getElementById('dashboard-log-preview');
  if (!el) return;
  const recent = allLogs.slice(0, 8);
  if (recent.length === 0) {
    el.innerHTML = `<div class="loading-text">รอ Log ระบบ...</div>`;
    return;
  }
  el.innerHTML = recent.map(l => {
    const t = new Date(l.timestamp).toLocaleTimeString('th-TH', { timeZone: 'Asia/Bangkok', hour12: false });
    return `<div class="log-mini-entry">
      <span class="log-mini-time">${t}</span>
      <span class="log-mini-agent">${escHtml(l.agent_name)}</span>
      <span class="log-mini-msg">${escHtml(l.message.substring(0, 80))}</span>
    </div>`;
  }).join('');
}

// ══════════════════════════════════════════════════════════════
//  PAGE: BOARDROOM
// ══════════════════════════════════════════════════════════════
async function loadBoardroom() {
  try {
    const rooms = allRooms.department_rooms ? allRooms : await apiGet('/api/telegram/rooms');
    allRooms = rooms;
    renderBoardroomParticipants(rooms);
  } catch (err) {
    console.error(err);
  }
}

function renderBoardroomParticipants(rooms) {
  const depts = rooms.department_rooms || {};
  const pmEl = document.getElementById('pm-participants');
  const mentEl = document.getElementById('mention-buttons');

  pmEl.innerHTML = Object.entries(depts)
    .filter(([id]) => id !== '01_secretary')
    .map(([id, d]) => `
      <div class="participant-row">
        <span class="p-avatar">🤖</span>
        <div>
          <div class="p-name">${escHtml(d.pm_name || d.name)}</div>
          <div class="p-role">PM — ${escHtml(d.name)}</div>
        </div>
        <span class="p-status ${d.bot_token ? 'online' : ''}">•</span>
      </div>`).join('');

  mentEl.innerHTML = Object.entries(depts)
    .filter(([id]) => id !== '01_secretary')
    .map(([id, d]) => `<button class="mention-btn" onclick="insertMention('${escHtml(d.pm_name || d.name)}')">@${escHtml(d.pm_name || d.name)}</button>`)
    .join('');
}

function insertMention(name) {
  const ta = document.getElementById('boardroom-input');
  ta.value += `@${name} `;
  ta.focus();
}

function handleBoardroomKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendBoardroomMessage(); }
}

async function sendBoardroomMessage() {
  const ta = document.getElementById('boardroom-input');
  const text = ta.value.trim();
  if (!text) return;

  ta.value = '';
  addChatMessage('boardroom-messages', 'owner', '👑', 'Owner (คุณ)', text);

  const btn = document.getElementById('btn-boardroom-send');
  btn.disabled = true; btn.textContent = '...';

  const thinking = addChatMessage('boardroom-messages', 'thinking', '🏛️', 'คณะผู้บริหาร', 'กำลังอภิปรายและประมวลผลวาระประชุม...');

  try {
    const res = await apiPost('/api/telegram/director-meeting', { text });
    thinking.remove();
    const reply = res.reply || res.message || res.result || JSON.stringify(res, null, 2);
    const name = res.responder_name || 'คณะผู้บริหาร Boardroom';
    const avatar = res.responder_avatar || '🤖';
    addChatMessage('boardroom-messages', 'ai', avatar, name, reply);
  } catch (err) {
    thinking.remove();
    addChatMessage('boardroom-messages', 'ai', '❌', 'ระบบ Boardroom', 'เกิดข้อผิดพลาด: ' + err.message);
  } finally {
    btn.disabled = false; btn.textContent = 'ส่ง ↵';
  }
}

function addChatMessage(containerId, role, avatar, agentName, text) {
  const el = document.getElementById(containerId);
  const div = document.createElement('div');
  div.className = `chat-msg ${role}`;
  const time = new Date().toLocaleTimeString('th-TH', { timeZone: 'Asia/Bangkok', hour12: false });
  
  // แปลง \n ใน text เป็น <br/> และแสดง HTML แบบจำกัดเพื่อให้อ่านง่าย
  let formattedText = escHtml(text).replace(/\n/g, '<br/>');
  
  // คืนค่า tag ที่ปลอดภัยเบื้องต้น เช่น <b>, 🌟, 📌, 📋 เพื่อให้อ่านง่ายขึ้น
  formattedText = formattedText
    .replace(/&lt;b&gt;/g, '<strong>').replace(/&lt;\/b&gt;/g, '</strong>')
    .replace(/&lt;strong&gt;/g, '<strong>').replace(/&lt;\/strong&gt;/g, '</strong>')
    .replace(/&lt;code&gt;/g, '<code>').replace(/&lt;\/code&gt;/g, '</code>')
    .replace(/&lt;pre&gt;/g, '<pre>').replace(/&lt;\/pre&gt;/g, '</pre>');

  div.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div>
      ${agentName ? `<div class="msg-agent">${escHtml(agentName)}</div>` : ''}
      <div class="msg-bubble">${formattedText}</div>
      <div class="msg-time">${time}</div>
    </div>`;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
  return div;
}

// ══════════════════════════════════════════════════════════════
//  PAGE: TEAMS
// ══════════════════════════════════════════════════════════════
async function loadTeams() {
  try {
    const [agents, rooms] = await Promise.all([
      apiGet('/api/agents'),
      apiGet('/api/telegram/rooms'),
    ]);
    allAgents = agents;
    allRooms  = rooms;
    renderTeams(agents, rooms);
    updateAgentDeptSelect(rooms);

    // Sync sidebar badges
    const deptCount = new Set((agents || []).map(a => a.department)).size;
    const badgeTeams = document.getElementById('badge-teams');
    if (badgeTeams) badgeTeams.textContent = deptCount;
    const badgeWorkstations = document.getElementById('badge-workstations');
    if (badgeWorkstations) badgeWorkstations.textContent = (agents || []).length;
  } catch (err) {
    console.error(err);
    document.getElementById('teams-grid').innerHTML = `<div class="empty-state">❌ โหลดข้อมูลไม่สำเร็จ</div>`;
  }
}

function renderTeams(agents, rooms, filter = '') {
  const grid = document.getElementById('teams-grid');
  const depts = rooms.department_rooms || {};
  const agentsByDept = {};

  agents.forEach(a => {
    if (!agentsByDept[a.department]) agentsByDept[a.department] = [];
    agentsByDept[a.department].push(a);
  });

  const deptKeys = Object.keys(depts);
  // Also show departments that have agents but no room config
  const allKeys = [...new Set([...deptKeys, ...Object.keys(agentsByDept)])];

  const filtered = filter ? allKeys.filter(k => {
    const d = depts[k];
    const s = (d?.name + d?.pm_name + k).toLowerCase();
    return s.includes(filter.toLowerCase()) || (agentsByDept[k] || []).some(a => a.name.toLowerCase().includes(filter.toLowerCase()));
  }) : allKeys;

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1">
        <div class="empty-icon">🏢</div>
        <div>ยังไม่มีทีม</div>
        <button class="btn btn-primary" style="margin-top:12px" onclick="openCreateTeamModal()">＋ สร้างทีมแรก</button>
      </div>`;
    return;
  }

  grid.innerHTML = filtered.map(deptId => {
    const d = depts[deptId];
    const name    = d?.name    || deptId;
    const pmName  = d?.pm_name || '—';
    const token   = d?.bot_token;
    const dAgents = agentsByDept[deptId] || [];
    const isSecretary = deptId === '01_secretary';

    const avatarEmoji = isSecretary ? '🗂️' : '🏢';
    const tokenBadge  = `<span class="team-token-badge ok" title="สั่งงานได้โดยตรงผ่าน Telegram Enterprise Bot">🤖 สั่งงานผ่าน Telegram</span>`;

    const agentRows = dAgents.map(a => `
      <div class="agent-row">
        <span style="font-size:12px">${a.role.startsWith('pm') ? '👑' : '🤖'}</span>
        <span class="agent-row-name truncate">${escHtml(a.name)}</span>
        <span class="agent-row-model">${a.model.split('-')[0]}</span>
        <div class="agent-row-actions">
          <button class="btn btn-icon btn-sm" onclick="editAgent('${a.id}')" title="แก้ไข">✏️</button>
          <button class="btn btn-icon btn-sm btn-danger" onclick="deleteAgent('${a.id}')" title="ลบ">🗑️</button>
        </div>
      </div>`).join('');

    const footer = isSecretary ? `
      <div class="team-card-actions">
        <button class="btn btn-sm btn-primary btn-dispatch-main" onclick="openDeptDispatchModal('${deptId}')">🚀 สั่งงานเลขาอิงฟ้า</button>
        <div class="team-card-subactions">
          <button class="btn btn-sm" onclick="openEmployeeWorkstation('${deptId}')" title="ดูโต๊ะทำงาน AI">👤 โต๊ะทำงาน</button>
          <button class="btn btn-sm" onclick="openAvatarModal('${deptId}')" title="เปลี่ยนรูปประจำตัว AI">📷 เปลี่ยนรูป</button>
          <button class="btn btn-sm" onclick="openSecretaryChat()" title="ปรึกษาส่วนตัวกับอิงฟ้า">💬 คุยกับอิงฟ้า</button>
          <button class="btn btn-sm" onclick="openCreateAgentForDept('${deptId}')" title="เพิ่ม Agent ภายใต้สำนักนี้">＋ Agent</button>
        </div>
      </div>
    ` : `
      <div class="team-card-actions">
        <button class="btn btn-sm btn-primary btn-dispatch-main" onclick="openDeptDispatchModal('${deptId}')">🚀 สั่งงานแผนกนี้</button>
        <div class="team-card-subactions">
          <button class="btn btn-sm" onclick="openEmployeeWorkstation('${deptId}')" title="ดูโต๊ะทำงาน AI">👤 โต๊ะทำงาน</button>
          <button class="btn btn-sm" onclick="openAvatarModal('${deptId}')" title="เปลี่ยนรูปประจำตัว AI">📷 เปลี่ยนรูป</button>
          <button class="btn btn-sm" onclick="openDirectCommandModal('${deptId}', '${escHtml(name)}')" title="สั่งงานตรงแผนกนี้">💬 สั่งตรง</button>
          <button class="btn btn-sm" onclick="openCreateAgentForDept('${deptId}')" title="เพิ่ม Agent ภายใต้แผนกนี้">＋ Agent</button>
          ${!token ? `<button class="btn btn-sm btn-outline-warning" onclick="setTokenForTeam('${deptId}', '${escHtml(name)}')" title="ตั้งค่า Bot Token">🔑 Token</button>` : ''}
          <button class="btn btn-sm btn-danger btn-icon" onclick="deleteTeam('${deptId}', '${escHtml(name)}')" title="ลบแผนก">🗑️</button>
        </div>
      </div>
    `;

    const pmAgent = dAgents.find(a => a.role && a.role.startsWith('pm')) || dAgents[0];
    const deptAvatarUrl = pmAgent?.avatar_url || `/static/img/avatars/${deptId}.png`;

    return `
      <div class="team-card" id="tc-${deptId}">
        <div class="team-card-head">
          <div class="team-avatar" style="cursor:pointer; overflow:hidden; padding:0; display:flex; align-items:center; justify-content:center; width:48px; height:48px; border-radius:50%; border:2px solid var(--border);" onclick="openEmployeeWorkstation('${deptId}')" title="คลิกเพื่อดูโต๊ะทำงาน">
            <img src="${deptAvatarUrl}" alt="${escHtml(name)}" style="width:100%; height:100%; object-fit:cover;" onerror="this.onerror=null; this.src='/static/img/avatars/${deptId}.jpg'; this.onerror=()=>{this.parentElement.innerHTML='${avatarEmoji}';};" />
          </div>
          <div class="team-info">
            <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
              <div class="team-name">${escHtml(name)}</div>
              <span class="badge badge-online" id="status-badge-${deptId}" style="padding:1px 6px; font-size:10px;">Online</span>
            </div>
            <div class="team-pm">PM: ${escHtml(pmName)}</div>
            <div class="team-id">${deptId}</div>
          </div>
          ${tokenBadge}
        </div>
        <div class="team-card-body">
          ${dAgents.length > 0
            ? `<div class="team-agents-list">${agentRows}</div>`
            : `<div class="empty-state" style="padding:10px 0;font-size:12px">ยังไม่มี Agent ในทีมนี้</div>`
          }
        </div>
        <div class="team-card-foot">${footer}</div>
      </div>`;
  }).join('');
}

function filterTeams(q) {
  renderTeams(allAgents, allRooms, q);
}

function updateAgentDeptSelect(rooms) {
  const sel = document.getElementById('ca-dept');
  if (!sel) return;
  const depts = rooms.department_rooms || {};
  const agents = allAgents || [];
  const allKeys = [...new Set([...Object.keys(depts), ...agents.map(a => a.department)])];
  sel.innerHTML = allKeys.map(k => `<option value="${k}">${depts[k]?.name || k}</option>`).join('');
}

// ─── Create Team Modal ─────────────────────────────────────────
function openCreateTeamModal() {
  document.getElementById('ct-name').value = '';
  document.getElementById('ct-pm').value = '';
  document.getElementById('proposal-box').style.display = 'none';
  document.getElementById('proposal-box').innerHTML = '';
  _pendingProposal = null;
  openModal('modal-create-team');
}

async function proposeTeamStructure() {
  const name   = document.getElementById('ct-name').value.trim();
  const pmName = document.getElementById('ct-pm').value.trim();
  if (!name) { toast('กรุณาใส่ชื่อทีมก่อนค่ะ', 'warning'); return; }

  const btn = document.getElementById('btn-propose');
  btn.disabled = true; btn.textContent = '⏳ AI กำลังคิด...';

  try {
    const res = await apiPost('/api/telegram/propose-team', { name, pm_name: pmName });
    const p = res.proposal;
    _pendingProposal = p;

    const rolesHtml = (p.roles || []).map(r => `<span class="role-chip">🤖 ${escHtml(r)}</span>`).join('');
    const kpiHtml   = (p.kpis  || []).map((k, i) => `<div class="p-row">${i+1}. ${escHtml(k)}</div>`).join('');

    const box = document.getElementById('proposal-box');
    box.style.display = 'block';
    box.innerHTML = `
      <div class="p-title">💡 AI เสนอโครงสร้างทีม "${escHtml(p.name || name)}"</div>
      <div class="p-row"><strong>PM:</strong> ${escHtml(p.pm_name || pmName || 'ตั้งให้อัตโนมัติ')}</div>
      <div class="p-row"><strong>บทบาทสมาชิก:</strong><br/>${rolesHtml || '—'}</div>
      <div class="p-row" style="margin-top:8px"><strong>KPI เป้าหมาย:</strong></div>
      ${kpiHtml}
      <div class="p-row" style="margin-top:8px;color:var(--brand-400)">✅ กด <strong>อนุมัติและสร้างทีม</strong> เพื่อดำเนินการค่ะ</div>
    `;
  } catch (err) {
    toast('ไม่สามารถขอข้อเสนอ AI ได้: ' + err.message, 'error');
  } finally {
    btn.disabled = false; btn.textContent = '💡 ให้ AI เสนอโครงสร้างทีมและ KPI ที่เหมาะสม';
  }
}

async function confirmCreateTeam() {
  const name   = document.getElementById('ct-name').value.trim();
  const pmName = document.getElementById('ct-pm').value.trim();
  if (!name) { toast('กรุณาใส่ชื่อทีม', 'warning'); return; }

  const btn = document.getElementById('btn-confirm-team');
  btn.disabled = true; btn.textContent = '⏳ กำลังสร้าง...';

  try {
    await apiPost('/api/telegram/rooms', { name, pm_name: pmName });
    toast(`✅ สร้างทีม "${name}" สำเร็จ!`, 'success');
    closeModal('modal-create-team');
    await loadTeams();
    await loadDashboard();
  } catch (err) {
    toast('สร้างทีมไม่สำเร็จ: ' + err.message, 'error');
  } finally {
    btn.disabled = false; btn.textContent = '✅ อนุมัติและสร้างทีม';
  }
}

async function deleteTeam(deptId, name) {
  if (!confirm(`ลบทีม "${name}" และ Agent ทั้งหมดในทีมนี้ใช่ไหม?`)) return;
  try {
    await apiDelete(`/api/telegram/rooms/${deptId}`);
    toast(`ลบทีม "${name}" เรียบร้อย`, 'success');
    await loadTeams();
    await loadDashboard();
    if (typeof fetchSimulationState === 'function') await fetchSimulationState();
    if (typeof loadWorkstations === 'function') await loadWorkstations();
    if (typeof syncOfficeWithSimState === 'function') syncOfficeWithSimState();
  } catch (err) {
    toast('ลบทีมไม่สำเร็จ: ' + err.message, 'error');
  }
}

// ─── Create Agent Modal ────────────────────────────────────────
function openCreateAgentModal() {
  document.getElementById('ca-edit-id').value = '';
  document.getElementById('agent-modal-title').textContent = '🤖 สร้าง Agent ใหม่';
  document.getElementById('ca-name').value = '';
  document.getElementById('ca-pm-name').value = '';
  document.getElementById('ca-identity').value = '';
  document.getElementById('ca-job-desc').value = '';
  document.getElementById('ca-skill').value = '';
  document.getElementById('ca-temp').value = 0.5;
  document.getElementById('ca-temp-val').textContent = '0.5';
  
  // เรียกใช้ dynamic model list
  renderModelSelect('ca-model', 'gemini-1.5-flash');
  
  updateAgentDeptSelect(allRooms);
  const deptSelect = document.getElementById('ca-dept');
  if (deptSelect) deptSelect.disabled = false;
  openModal('modal-create-agent');
}

function openCreateAgentForDept(deptId) {
  openCreateAgentModal();
  const sel = document.getElementById('ca-dept');
  if (sel) sel.value = deptId;
}

async function editAgent(agentId) {
  try {
    const a = await apiGet(`/api/agents/${agentId}`);
    document.getElementById('ca-edit-id').value = a.id;
    document.getElementById('agent-modal-title').textContent = `✏️ แก้ไข Agent: ${a.name}`;
    document.getElementById('ca-name').value = a.name;
    document.getElementById('ca-pm-name').value = a.pm_name || '';
    
    // เรียกใช้ dynamic model list
    renderModelSelect('ca-model', a.model);
    
    document.getElementById('ca-temp').value = a.temperature;
    document.getElementById('ca-temp-val').textContent = a.temperature;
    document.getElementById('ca-identity').value = a.identity || '';
    document.getElementById('ca-job-desc').value = a.job_description || '';
    document.getElementById('ca-skill').value    = a.skill    || '';
    updateAgentDeptSelect(allRooms);
    const deptSelect = document.getElementById('ca-dept');
    if (deptSelect) {
      deptSelect.value = a.department;
      deptSelect.disabled = true;
    }
    openModal('modal-create-agent');
  } catch (err) {
    toast('โหลดข้อมูล Agent ไม่สำเร็จ', 'error');
  }
}

async function submitAgent() {
  const editId = document.getElementById('ca-edit-id').value;
  const data = {
    name:            document.getElementById('ca-name').value.trim(),
    pm_name:         document.getElementById('ca-pm-name').value.trim(),
    department:      document.getElementById('ca-dept').value,
    model:           document.getElementById('ca-model').value,
    temperature:     parseFloat(document.getElementById('ca-temp').value),
    identity:        document.getElementById('ca-identity').value.trim(),
    job_description: document.getElementById('ca-job-desc').value.trim(),
    skill:           document.getElementById('ca-skill').value.trim(),
  };

  if (!data.name || !data.identity || !data.skill || !data.job_description) {
    toast('กรุณากรอกข้อมูลให้ครบทุกช่อง (*)', 'warning'); return;
  }

  const btn = document.querySelector('#modal-create-agent .btn-primary');
  btn.disabled = true; btn.textContent = '⏳ กำลังบันทึก...';

  try {
    if (editId) {
      await apiPut(`/api/agents/${editId}`, {
        name: data.name,
        pm_name: data.pm_name,
        model: data.model,
        temperature: data.temperature,
        identity: data.identity,
        job_description: data.job_description,
        skill: data.skill,
      });
      toast(`✅ แก้ไข Agent "${data.name}" สำเร็จ!`, 'success');
    } else {
      await apiPost('/api/agents', data);
      toast(`✅ สร้าง Agent "${data.name}" สำเร็จ!`, 'success');
    }
    closeModal('modal-create-agent');
    await loadTeams();
    await loadDashboard();
    if (typeof loadWorkstation === 'function') {
      try { await loadWorkstation(); } catch (e) {}
    }
  } catch (err) {
    toast('บันทึก Agent ไม่สำเร็จ: ' + err.message, 'error');
  } finally {
    btn.disabled = false; btn.textContent = '💾 บันทึก Agent';
  }
}

async function deleteAgent(agentId) {
  if (!confirm(`ลบ Agent "${agentId}" ใช่ไหม?`)) return;
  try {
    await apiDelete(`/api/agents/${agentId}`);
    toast('ลบ Agent เรียบร้อย', 'success');
    await loadTeams();
    await loadDashboard();
    if (typeof fetchSimulationState === 'function') await fetchSimulationState();
    if (typeof loadWorkstations === 'function') await loadWorkstations();
    if (typeof syncOfficeWithSimState === 'function') syncOfficeWithSimState();
  } catch (err) {
    toast('ลบ Agent ไม่สำเร็จ: ' + err.message, 'error');
  }
}

// ─── Direct Command Modal ─────────────────────────────────────
function openDirectCommandModal(deptId, name) {
  document.getElementById('dc-dept-id').value = deptId;
  document.getElementById('dc-team-name').textContent = name;
  document.getElementById('dc-text').value = '';
  document.getElementById('dc-result').style.display = 'none';
  openModal('modal-direct-cmd');
}

async function sendDirectCommand() {
  const deptId = document.getElementById('dc-dept-id').value;
  const text   = document.getElementById('dc-text').value.trim();
  if (!text) { toast('กรุณาพิมพ์คำสั่ง', 'warning'); return; }

  const btn = document.getElementById('btn-dc-send');
  btn.disabled = true; btn.textContent = '⏳ กำลังส่ง...';

  try {
    const res = await apiPost('/api/telegram/direct-command', { dept_id: deptId, text });
    const result = document.getElementById('dc-result');
    result.style.display = 'block';
    result.textContent = res.reply || res.message || res.result || JSON.stringify(res, null, 2);
    toast('✅ ส่งคำสั่งสำเร็จ!', 'success');
  } catch (err) {
    toast('ส่งคำสั่งไม่สำเร็จ: ' + err.message, 'error');
  } finally {
    btn.disabled = false; btn.textContent = '📨 ส่งคำสั่ง';
  }
}

// ─── Set Token for Team ────────────────────────────────────────
async function setTokenForTeam(deptId, name) {
  const token = prompt(`🔑 กรอก Bot Token สำหรับ PM ทีม "${name}"\n(รับได้จาก @BotFather ใน Telegram)`);
  if (!token?.trim()) return;

  try {
    await apiPost('/api/telegram/rooms', {
      name: name, pm_name: '', id: deptId, bot_token: token.trim(),
    });
    toast(`✅ ตั้งค่า Bot Token ทีม "${name}" สำเร็จ!`, 'success');
    await loadTeams();
  } catch (err) {
    toast('ตั้งค่า Token ไม่สำเร็จ: ' + err.message, 'error');
  }
}

// ══════════════════════════════════════════════════════════════
//  PAGE: LOGS
// ══════════════════════════════════════════════════════════════
async function loadLogs() {
  const container = document.getElementById('log-stream');

  // Load initial logs from API
  try {
    const [logs, agents] = await Promise.all([
      apiGet('/api/logs?limit=200'),
      apiGet('/api/agents')
    ]);
    allLogs = logs;
    allAgents = agents;
    renderLogStream(logs);

    // Populate agent filter (ใช้เฉพาะ Agent ที่ผู้ใช้สร้างจริง + System / Boardroom)
    const agentNames = new Set(agents.map(a => a.name));
    agentNames.add('System');
    agentNames.add('เลขา AI');
    agentNames.add('เลขา AI (อิงฟ้า - เพื่อนคู่คิดบริหาร)');
    agentNames.add('คณะผู้บริหาร & PM Boardroom');

    const sortedAgents = Array.from(agentNames).sort();
    const sel = document.getElementById('log-agent-filter');
    sel.innerHTML = `<option value="">ทุก Agent</option>` + sortedAgents.map(a => `<option value="${a}">${a}</option>`).join('');
  } catch {
    container.innerHTML = `<div class="empty-state">❌ โหลด Logs ไม่สำเร็จ</div>`;
  }
}

function renderLogStream(logs) {
  const container = document.getElementById('log-stream');
  if (logs.length === 0) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">📋</div><div>ยังไม่มี Log</div></div>`;
    return;
  }
  container.innerHTML = logs.map(logEntryHtml).join('');
}

function logEntryHtml(l) {
  const t = new Date(l.timestamp).toLocaleString('th-TH', {
    timeZone: 'Asia/Bangkok', hour12: false,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
  const thought = l.thought_process
    ? `<div class="log-thought">💭 ${escHtml(l.thought_process.substring(0, 200))}</div>` : '';
  return `<div class="log-entry ${l.level}">
    <span class="log-time">${t}</span>
    <span class="log-agent truncate">${escHtml(l.agent_name)}</span>
    <span class="log-level ${l.level}">${l.level}</span>
    <div class="log-msg">${escHtml(l.message)}${thought}</div>
  </div>`;
}

function prependLogEntry(entry) {
  const container = document.getElementById('log-stream');
  if (!container) return;
  const loading = container.querySelector('.loading-text, .empty-state');
  if (loading) loading.remove();

  const div = document.createElement('div');
  div.innerHTML = logEntryHtml(entry);
  container.insertBefore(div.firstElementChild, container.firstChild);

  const auto = document.getElementById('log-autoscroll')?.checked;
  if (auto) container.scrollTop = 0;

  // Keep max 300 entries
  while (container.children.length > 300) container.lastChild.remove();
}

function filterLogs() {
  const level  = document.getElementById('log-level-filter').value;
  const agent  = document.getElementById('log-agent-filter').value;
  const search = document.getElementById('log-search').value.toLowerCase();

  const filtered = allLogs.filter(l => {
    if (level  && l.level !== level) return false;
    if (agent) {
      // ให้ match ค่อนข้างยืดหยุ่น เช่น "การตลาด AI" จะตรงกับ "PM การตลาด AI" ด้วย
      const aName = agent.toLowerCase();
      const logName = l.agent_name.toLowerCase();
      if (!logName.includes(aName) && !aName.includes(logName)) return false;
    }
    if (search && !l.message.toLowerCase().includes(search) && !l.agent_name.toLowerCase().includes(search)) return false;
    return true;
  });

  renderLogStream(filtered);
}

function clearLogFilter() {
  document.getElementById('log-level-filter').value = '';
  document.getElementById('log-agent-filter').value = '';
  document.getElementById('log-search').value = '';
  filterLogs();
}

// ══════════════════════════════════════════════════════════════
//  PAGE: SETTINGS
// ══════════════════════════════════════════════════════════════
// Track which settings are already configured (masked)
let _settingsState = {};

const AVAILABLE_MODEL_OPTIONS = [
  { id: 'gemini-1.5-flash', label: '⚡ Gemini 1.5 Flash (เร็ว / ประหยัด / งานทั่วไป)' },
  { id: 'gemini-1.5-pro', label: '🧠 Gemini 1.5 Pro (ฉลาด / วิเคราะห์ลึก)' },
  { id: 'gemini-2.0-flash-exp', label: '🚀 Gemini 2.0 Flash (โมเดลล่าสุด เร็วพิเศษ)' },
  { id: 'claude-3-5-sonnet-20241022', label: '🎭 Claude 3.5 Sonnet (งานเขียน / โค้ดดิ้ง)' },
  { id: 'claude-3-haiku-20240307', label: '⚡ Claude 3 Haiku (รวดเร็ว / สรุปย่อ)' },
  { id: 'llama3:latest', label: '🦙 Llama 3 (Local Ollama ฟรี 100%)' }
];

let allAvailableModels = AVAILABLE_MODEL_OPTIONS.map(m => m.id);

async function loadSettings() {
  try {
    const [s, rooms] = await Promise.all([
      apiGet('/api/settings'),
      apiGet('/api/telegram/rooms'),
    ]);
    allRooms = rooms;

    // Store which fields are already configured (not empty)
    _settingsState = {
      gemini_api_key:             !!s.gemini_configured,
      anthropic_api_key:          !!s.anthropic_configured,
      telegram_bot_token:         !!s.telegram_configured,
      telegram_owner_direct_chat_id: !!(s.telegram_owner_direct_chat_id),
    };
    _revealedSecrets = {};

    // Show masked placeholder for sensitive fields
    setMaskedInput('s-gemini-key', s.gemini_configured, s.gemini_api_key, 's-gemini-status');
    setMaskedInput('s-claude-key', s.anthropic_configured, s.anthropic_api_key, 's-claude-status');
    setMaskedInput('s-tg-token',   s.telegram_configured,  s.telegram_bot_token, 's-tg-token-status');

    // Plain text fields — fill directly
    const directChatInp = document.getElementById('s-direct-chat');
    if (directChatInp) {
      directChatInp.value = s.telegram_owner_direct_chat_id || '';
      delete directChatInp.dataset.action;
    }
    document.getElementById('s-owner-name').value = s.owner_name || '';
    document.getElementById('s-owner-identity').value = s.owner_identity || '';
    document.getElementById('s-owner-skill').value = s.owner_skill || '';

    // เก็บรายชื่อโมเดลทั้งหมดไว้สร้าง Dropdown
    const rawModels = s.available_models || '';
    allAvailableModels = rawModels.split(',').map(m => m.trim()).filter(m => m);
    if (allAvailableModels.length === 0) {
      allAvailableModels = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash-exp', 'claude-3-5-sonnet-20241022', 'claude-3-haiku-20240307'];
    }

    // สร้าง dropdown แบบ dynamic
    renderModelSelect('s-default-model', s.default_model);

    // Badges
    const llmOk = s.gemini_configured || s.anthropic_configured;
    document.getElementById('llm-status').className = `badge ${llmOk ? 'badge-online' : ''}`;
    document.getElementById('llm-status').textContent = llmOk ? '✓ ตั้งค่าแล้ว' : '✗ ยังไม่ตั้งค่า';

    const tgOk = s.telegram_configured;
    document.getElementById('tg-status').className = `badge ${tgOk ? 'badge-online' : ''}`;
    document.getElementById('tg-status').textContent = tgOk ? '✓ ตั้งค่าแล้ว' : '✗ ยังไม่ตั้งค่า';
  } catch (err) {
    console.error('[loadSettings]', err);
    toast('โหลดการตั้งค่าไม่สำเร็จ: ' + err.message, 'error');
  }
}

let _revealedSecrets = {};

function renderModelSelect(selectId, selectedValue = '') {
  const sel = document.getElementById(selectId);
  if (!sel) return;

  const modelMap = {};
  AVAILABLE_MODEL_OPTIONS.forEach(m => { modelMap[m.id] = m.label; });

  let models = (allAvailableModels && allAvailableModels.length > 0)
    ? [...allAvailableModels]
    : AVAILABLE_MODEL_OPTIONS.map(m => m.id);

  // If selectedValue is not in list, add it at the top so it's not lost
  if (selectedValue && !models.includes(selectedValue)) {
    models.unshift(selectedValue);
  }

  sel.innerHTML = models.map(m => {
    let label = modelMap[m];
    if (!label) {
      if (m.includes('flash-exp') || m.includes('2.0-flash')) label = `🚀 ${m} (ล่าสุด / เร็วพิเศษ)`;
      else if (m.includes('flash')) label = `⚡ ${m} (เร็ว / ประหยัด)`;
      else if (m.includes('pro')) label = `🧠 ${m} (ฉลาด / ละเอียด)`;
      else if (m.includes('sonnet')) label = `🎭 ${m} (Anthropic Premium)`;
      else if (m.includes('haiku')) label = `⚡ ${m} (Anthropic เร็ว)`;
      else if (m.includes('llama')) label = `🦙 ${m} (Local Ollama ฟรี)`;
      else label = `🤖 ${m}`;
    }
    const isSel = (m === selectedValue) ? ' selected' : '';
    return `<option value="${escHtml(m)}"${isSel}>${escHtml(label)}</option>`;
  }).join('');

  if (selectedValue) {
    sel.value = selectedValue;
  }
}

function setMaskedInput(inputId, isConfigured, maskedValue, badgeId) {
  const input = document.getElementById(inputId);
  const badge = document.getElementById(badgeId);
  const btnToggle = document.getElementById('btn-toggle-' + inputId);
  if (!input || !badge) return;

  // Clear actual value (user must re-type or click reveal)
  input.value = '';
  input.type = 'password';
  delete input.dataset.action;
  if (btnToggle) btnToggle.textContent = '👁️ ดู';

  if (isConfigured) {
    // Show last 6 chars hint in placeholder
    const hint = maskedValue ? maskedValue.replace(/•+/, '').slice(-6) : '...';
    input.placeholder = `ตั้งค่าแล้ว (••••••${hint}) — พิมพ์ใหม่หรือกดดู/ล้างค่า`;
    badge.className   = 'config-badge ok';
    badge.textContent = '✓ ตั้งค่าแล้ว';
  } else {
    input.placeholder = inputId === 's-gemini-key' ? 'AIzaSy...'
      : inputId === 's-claude-key' ? 'sk-ant-...'
      : '123456789:ABCdefGHI...';
    badge.className   = 'config-badge warn';
    badge.textContent = '✗ ยังไม่ตั้งค่า';
  }

  input.oninput = () => {
    onSecretInputChange(input, badgeId, isConfigured);
  };
}

function onSecretInputChange(input, badgeId, isConfigured) {
  delete input.dataset.action;
  const badge = document.getElementById(badgeId);
  if (input.value.trim().length > 0) {
    if (badge) {
      badge.className = 'config-badge ok';
      badge.textContent = '✏️ แก้ไขแล้ว (รอกดบันทึก)';
    }
  } else if (!isConfigured) {
    if (badge) {
      badge.className = 'config-badge warn';
      badge.textContent = '✗ ยังไม่ตั้งค่า';
    }
  } else {
    if (badge) {
      badge.className = 'config-badge ok';
      badge.textContent = '✓ ตั้งค่าแล้ว';
    }
  }
}

// ─── Toggle Secret Visibility (👁️ / 🙈) ────────────────────────
async function toggleSecretVisibility(inputId) {
  const input = document.getElementById(inputId);
  const btn = document.getElementById('btn-toggle-' + inputId);
  if (!input) return;

  if (input.type === 'password') {
    // If input is empty and not actively cleared, try fetching stored secret to show
    if (!input.value && input.dataset.action !== 'clear') {
      try {
        if (!Object.keys(_revealedSecrets).length) {
          if (btn) btn.textContent = '⏳...';
          _revealedSecrets = await apiGet('/api/settings/reveal');
        }
        let secret = '';
        if (inputId === 's-gemini-key') secret = _revealedSecrets.gemini_api_key || '';
        else if (inputId === 's-claude-key') secret = _revealedSecrets.anthropic_api_key || '';
        else if (inputId === 's-tg-token') secret = _revealedSecrets.telegram_bot_token || '';
        if (secret) {
          input.value = secret;
        }
      } catch (e) {
        console.error('Error revealing secret:', e);
      }
    }
    input.type = 'text';
    if (btn) btn.textContent = '🙈 ซ่อน';
  } else {
    input.type = 'password';
    if (btn) btn.textContent = '👁️ ดู';
  }
}

function togglePasswordVisibility(inputId) {
  const input = document.getElementById(inputId);
  const btn = document.getElementById('btn-toggle-' + inputId);
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    if (btn) btn.textContent = '🙈 ซ่อน';
  } else {
    input.type = 'password';
    if (btn) btn.textContent = '👁️ ดู';
  }
}

// ─── Clear Secret Input (✕ ล้างค่า) ───────────────────────────
function clearSecretInput(inputId, deptId) {
  const input = document.getElementById(inputId);
  if (!input) return;

  input.value = '';
  input.dataset.action = 'clear';
  input.placeholder = '✕ ล้างค่าแล้ว — กดบันทึกเพื่อยกเลิกใช้งาน';

  let badgeId = '';
  if (inputId === 's-gemini-key') badgeId = 's-gemini-status';
  else if (inputId === 's-claude-key') badgeId = 's-claude-status';
  else if (inputId === 's-tg-token') badgeId = 's-tg-token-status';

  if (badgeId) {
    const badge = document.getElementById(badgeId);
    if (badge) {
      badge.className = 'config-badge warn';
      badge.textContent = '🗑️ ล้างค่า (กดบันทึกเพื่อยกเลิก)';
    }
  }

  const btnToggle = document.getElementById('btn-toggle-' + inputId);
  if (btnToggle) btnToggle.textContent = '👁️ ดู';

  toast('ล้างข้อมูลในช่องแล้ว — กดปุ่มบันทึกเพื่อยกเลิกการใช้งานออกจากระบบค่ะ', 'info');
}

// ─── Helper: call PUT /api/settings and show save result ──────
async function _doSaveSettings(body, btnId, statusId, btnLabel) {
  const btn    = document.getElementById(btnId);
  const status = document.getElementById(statusId);
  if (btn) { btn.disabled = true; btn.textContent = '⏳ กำลังบันทึก...'; }
  if (status) status.textContent = '';

  // Remove any untouched fields (keep empty strings "" if user explicitly cleared a field)
  const cleaned = {};
  Object.entries(body).forEach(([k, v]) => {
    if (v !== null && v !== undefined) {
      cleaned[k] = v;
    }
  });

  if (Object.keys(cleaned).length === 0) {
    toast('ไม่มีข้อมูลใหม่ให้บันทึก — กรุณาพิมพ์ค่าใหม่หรือกดล้างค่าก่อนค่ะ', 'warning');
    if (btn) { btn.disabled = false; btn.textContent = btnLabel; }
    return false;
  }

  try {
    await apiPut('/api/settings', cleaned);
    toast('✅ บันทึกสำเร็จ!', 'success');
    if (status) { status.textContent = '✅ บันทึกแล้ว'; setTimeout(() => { if (status) status.textContent = ''; }, 3000); }
    await loadSettings();
    return true;
  } catch (err) {
    toast('บันทึกไม่สำเร็จ: ' + err.message, 'error');
    if (status) { status.textContent = '❌ ไม่สำเร็จ'; setTimeout(() => { if (status) status.textContent = ''; }, 3000); }
    return false;
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = btnLabel; }
  }
}

// ─── Per-section save functions ───────────────────────────────
async function saveLLMSection() {
  const geminiInp = document.getElementById('s-gemini-key');
  const claudeInp = document.getElementById('s-claude-key');
  const body = {};

  if (geminiInp && geminiInp.dataset.action === 'clear') {
    body.gemini_api_key = "";
  } else if (geminiInp && geminiInp.value.trim()) {
    body.gemini_api_key = geminiInp.value.trim();
  }

  if (claudeInp && claudeInp.dataset.action === 'clear') {
    body.anthropic_api_key = "";
  } else if (claudeInp && claudeInp.value.trim()) {
    body.anthropic_api_key = claudeInp.value.trim();
  }

  const defaultModel = document.getElementById('s-default-model')?.value;
  if (defaultModel) body.default_model = defaultModel;

  await _doSaveSettings(body, 'btn-save-llm', 'save-status-llm', '💾 บันทึก LLM Keys');
}

async function saveTelegramSection() {
  const tgInp = document.getElementById('s-tg-token');
  const directInp = document.getElementById('s-direct-chat');
  const body = {};

  if (tgInp && tgInp.dataset.action === 'clear') {
    body.telegram_bot_token = "";
  } else if (tgInp && tgInp.value.trim()) {
    body.telegram_bot_token = tgInp.value.trim();
  }

  if (directInp && directInp.dataset.action === 'clear') {
    body.telegram_owner_direct_chat_id = "";
  } else if (directInp && directInp.value.trim() !== '') {
    body.telegram_owner_direct_chat_id = directInp.value.trim();
  }

  await _doSaveSettings(body, 'btn-save-tg', 'save-status-tg', '💾 บันทึก Telegram Settings');
}

async function saveOwnerSection() {
  const body = {
    owner_name:     document.getElementById('s-owner-name').value.trim() || null,
    owner_identity: document.getElementById('s-owner-identity').value.trim() || null,
    owner_skill:    document.getElementById('s-owner-skill').value.trim() || null,
  };
  Object.keys(body).forEach(k => { if (!body[k]) delete body[k]; });
  await _doSaveSettings(body, 'btn-save-owner', 'save-status-owner', '💾 บันทึก Owner Profile');
}

// ─── Save All Settings ───────────────────────────────────────
async function saveSettings() {
  const btn    = document.getElementById('btn-save');
  const status = document.getElementById('save-status');
  btn.disabled = true; btn.textContent = '⏳ กำลังบันทึกทั้งหมด...';
  status.textContent = '';

  const body = {};
  const geminiInp = document.getElementById('s-gemini-key');
  const claudeInp = document.getElementById('s-claude-key');
  const tgInp = document.getElementById('s-tg-token');
  const directInp = document.getElementById('s-direct-chat');

  if (geminiInp && geminiInp.dataset.action === 'clear') {
    body.gemini_api_key = "";
  } else if (geminiInp && geminiInp.value.trim()) {
    body.gemini_api_key = geminiInp.value.trim();
  }

  if (claudeInp && claudeInp.dataset.action === 'clear') {
    body.anthropic_api_key = "";
  } else if (claudeInp && claudeInp.value.trim()) {
    body.anthropic_api_key = claudeInp.value.trim();
  }

  const defaultModel = document.getElementById('s-default-model')?.value;
  if (defaultModel) body.default_model = defaultModel;

  if (tgInp && tgInp.dataset.action === 'clear') {
    body.telegram_bot_token = "";
  } else if (tgInp && tgInp.value.trim()) {
    body.telegram_bot_token = tgInp.value.trim();
  }

  if (directInp && directInp.dataset.action === 'clear') {
    body.telegram_owner_direct_chat_id = "";
  } else if (directInp && directInp.value.trim() !== '') {
    body.telegram_owner_direct_chat_id = directInp.value.trim();
  }

  const ownerName = document.getElementById('s-owner-name')?.value.trim();
  if (ownerName !== undefined && ownerName !== '') body.owner_name = ownerName;

  const ownerIdent = document.getElementById('s-owner-identity')?.value.trim();
  if (ownerIdent !== undefined && ownerIdent !== '') body.owner_identity = ownerIdent;

  const ownerSkill = document.getElementById('s-owner-skill')?.value.trim();
  if (ownerSkill !== undefined && ownerSkill !== '') body.owner_skill = ownerSkill;

  if (Object.keys(body).length === 0) {
    toast('ไม่มีข้อมูลใหม่หรือคำสั่งล้างค่าให้บันทึก — กรุณาพิมพ์ค่าใหม่หรือกดล้างค่าก่อนค่ะ', 'warning');
    btn.disabled = false; btn.textContent = '💾 บันทึกทั้งหมด';
    return;
  }

  try {
    await apiPut('/api/settings', body);
    toast('✅ บันทึกการตั้งค่าทั้งหมดสำเร็จ!', 'success');
    status.textContent = '✅ บันทึกเรียบร้อย';
    await loadSettings();
  } catch (err) {
    toast('บันทึกไม่สำเร็จ: ' + err.message, 'error');
    status.textContent = '❌ บันทึกไม่สำเร็จ';
  } finally {
    btn.disabled = false; btn.textContent = '💾 บันทึกทั้งหมด';
    setTimeout(() => { status.textContent = ''; }, 4000);
  }
}

async function testAllConnections() {
  const panel = document.getElementById('test-results');
  const body  = document.getElementById('test-results-body');
  panel.style.display = 'block';
  body.innerHTML = `<div class="loading-text"><span class="spinning">⏳</span> กำลังทดสอบการเชื่อมต่อ...</div>`;

  try {
    const res = await apiPost('/api/settings/test', {});
    // results is a dict {telegram: {...}, gemini: {...}, anthropic: {...}}
    const results = res.results || res;
    const names = { telegram: '🤖 Telegram Bot', gemini: '🧠 Gemini API', anthropic: '🎭 Claude API' };
    const items = Object.entries(results);
    body.innerHTML = items.map(([key, r]) => `
      <div class="test-row">
        <span class="test-icon">${r.ok ? '✅' : '❌'}</span>
        <span style="flex:1">${names[key] || key}</span>
        <span style="color:${r.ok ? 'var(--success)' : 'var(--error)'};font-size:12px">${escHtml(r.message || '')}</span>
      </div>`).join('') || `<div class="test-row">✅ ระบบทำงานปกติ</div>`;
  } catch (err) {
    body.innerHTML = `<div class="test-row"><span>❌</span> ทดสอบไม่สำเร็จ: ${escHtml(err.message)}</div>`;
  }
}

async function testTelegramMessage() {
  const chatId = document.getElementById('s-direct-chat').value.trim();
  if (!chatId) { toast('กรุณาใส่ Direct Chat ID ก่อนค่ะ', 'warning'); return; }
  try {
    await apiPost('/api/settings/test-message', { chat_id: chatId });
    toast('✅ ส่งข้อความทดสอบสำเร็จ! กรุณาตรวจสอบใน Telegram', 'success');
  } catch (err) {
    toast('ส่งไม่สำเร็จ: ' + err.message, 'error');
  }
}

// ══════════════════════════════════════════════════════════════
//  Secretary Chat
// ══════════════════════════════════════════════════════════════
function openSecretaryChat() {
  openModal('modal-secretary');
  document.getElementById('secretary-input')?.focus();
}

function handleSecretaryKey(e) {
  if (e.key === 'Enter') { e.preventDefault(); sendSecretaryMessage(); }
}

async function sendSecretaryMessage() {
  const input = document.getElementById('secretary-input');
  const text  = input.value.trim();
  if (!text) return;

  input.value = '';
  addChatMessage('secretary-messages', 'owner', '👑', '', text);

  const btn = document.getElementById('btn-secretary-send');
  btn.disabled = true; btn.textContent = '...';

  const thinking = addChatMessage('secretary-messages', 'thinking', '🗂️', 'อิงฟ้า', 'กำลังคิด...');

  try {
    const res = await apiPost('/api/telegram/simulate', { text });
    thinking.remove();
    const reply = res.reply || res.message || res.result || JSON.stringify(res, null, 2);
    addChatMessage('secretary-messages', 'ai', '🗂️', 'อิงฟ้า', reply);
  } catch (err) {
    thinking.remove();
    addChatMessage('secretary-messages', 'ai', '❌', 'ระบบ', 'เกิดข้อผิดพลาด: ' + err.message);
  } finally {
    btn.disabled = false; btn.textContent = 'ส่ง';
  }
}

// ─── Utilities ─────────────────────────────────────────────────
function escHtml(s) {
  if (!s) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ══════════════════════════════════════════════════════════════
//  AI Model Usage Tracking
// ══════════════════════════════════════════════════════════════
let currentUsageLimits = { monthly_token_limit: 10000000, monthly_cost_limit: 50.0 };

async function loadUsageStats() {
  try {
    const summary = await apiGet('/api/usage');
    
    // Save current limits to memory
    currentUsageLimits.monthly_token_limit = summary.monthly_limit_tokens;
    currentUsageLimits.monthly_cost_limit = summary.monthly_limit_cost;
    
    // 1. Tokens progress bar
    const tokenRatio = `${summary.month_used_tokens.toLocaleString()} / ${summary.monthly_limit_tokens.toLocaleString()} Tokens`;
    const tokensRatioEl = document.getElementById('usage-tokens-ratio');
    if (tokensRatioEl) tokensRatioEl.textContent = tokenRatio;
    
    const tokenPercentVal = Math.min(100, Math.round((summary.month_used_tokens / summary.monthly_limit_tokens) * 100));
    const tokensPercentEl = document.getElementById('usage-tokens-percent');
    if (tokensPercentEl) tokensPercentEl.textContent = `${tokenPercentVal}%`;
    
    const tokensFillEl = document.getElementById('usage-tokens-fill');
    if (tokensFillEl) tokensFillEl.style.width = `${tokenPercentVal}%`;
    
    const tokensRemainingEl = document.getElementById('usage-tokens-remaining');
    if (tokensRemainingEl) tokensRemainingEl.textContent = `เหลือ ${summary.month_remaining_tokens.toLocaleString()} Tokens`;
    
    // 2. Cost progress bar
    const costRatio = `$${summary.month_used_cost.toFixed(4)} / $${summary.monthly_limit_cost.toFixed(2)} USD`;
    const costRatioEl = document.getElementById('usage-cost-ratio');
    if (costRatioEl) costRatioEl.textContent = costRatio;
    
    const costPercentVal = Math.min(100, Math.round((summary.month_used_cost / summary.monthly_limit_cost) * 100));
    const costPercentEl = document.getElementById('usage-cost-percent');
    if (costPercentEl) costPercentEl.textContent = `${costPercentVal}%`;
    
    const costFillEl = document.getElementById('usage-cost-fill');
    if (costFillEl) costFillEl.style.width = `${costPercentVal}%`;
    
    const costRemainingEl = document.getElementById('usage-cost-remaining');
    if (costRemainingEl) costRemainingEl.textContent = `เหลือ $${summary.month_remaining_cost.toFixed(4)} USD`;
    
    // 3. Mini Stats
    const todayTokensEl = document.getElementById('usage-today-tokens');
    if (todayTokensEl) todayTokensEl.textContent = summary.today_used_tokens.toLocaleString();
    
    const todayCostEl = document.getElementById('usage-today-cost');
    if (todayCostEl) todayCostEl.textContent = `$${summary.today_used_cost.toFixed(4)}`;
    
    const monthRequestsEl = document.getElementById('usage-month-requests');
    if (monthRequestsEl) monthRequestsEl.textContent = summary.month_requests.toLocaleString();
    
    // 4. Usage history rows
    const tbody = document.getElementById('usage-history-rows');
    if (tbody) {
      if (summary.history && summary.history.length > 0) {
        tbody.innerHTML = summary.history.map(row => `
          <tr>
            <td><strong>${row.date}</strong></td>
            <td>${row.requests.toLocaleString()} ครั้ง</td>
            <td>${row.tokens.toLocaleString()} Tokens</td>
            <td><span style="color:var(--brand-400); font-weight:500;">$${row.cost.toFixed(4)}</span></td>
          </tr>
        `).join('');
      } else {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; opacity:0.5;">ยังไม่มีประวัติการใช้งาน</td></tr>`;
      }
    }
  } catch (err) {
    console.error('Failed to load usage stats:', err);
  }
}

function openLimitsModal() {
  const limTokensEl = document.getElementById('lim-tokens');
  if (limTokensEl) limTokensEl.value = currentUsageLimits.monthly_token_limit;
  
  const limCostEl = document.getElementById('lim-cost');
  if (limCostEl) limCostEl.value = currentUsageLimits.monthly_cost_limit;
  
  openModal('modal-limits-config');
}

async function submitLimitsConfig() {
  const tokenLimit = parseInt(document.getElementById('lim-tokens').value, 10);
  const costLimit = parseFloat(document.getElementById('lim-cost').value);
  
  if (isNaN(tokenLimit) || isNaN(costLimit) || tokenLimit <= 0 || costLimit <= 0) {
    toast('กรุณากรอกข้อมูลตัวเลขที่ถูกต้อง', 'warning');
    return;
  }
  
  try {
    await apiPut('/api/usage/limits', {
      monthly_token_limit: tokenLimit,
      monthly_cost_limit: costLimit
    });
    toast('✅ บันทึกตั้งค่าลิมิตความปลอดภัยเรียบร้อย', 'success');
    closeModal('modal-limits-config');
    await loadUsageStats();
  } catch (err) {
    toast('บันทึกไม่สำเร็จ: ' + err.message, 'error');
  }
}

// ══════════════════════════════════════════════════════════════
//  Agent Processing Status Poller
// ══════════════════════════════════════════════════════════════
async function updateAgentStatuses() {
  try {
    const statuses = await apiGet('/api/agents/status/all');
    
    // Update all team cards
    if (allRooms && allRooms.department_rooms) {
      Object.keys(allRooms.department_rooms).forEach(deptId => {
        const badge = document.getElementById(`status-badge-${deptId}`);
        if (badge) {
          const state = statuses[deptId] || 'idle';
          if (state === 'processing') {
            badge.textContent = '⏳ กำลังทำงาน...';
            badge.className = 'badge badge-processing';
          } else {
            badge.textContent = 'Online';
            badge.className = 'badge badge-online';
          }
        }
      });
    }
    
    // Update secretary status on dashboard
    const secBadge = document.getElementById('status-badge-secretary');
    if (secBadge) {
      const state = statuses['01_secretary'] || 'idle';
      if (state === 'processing') {
        secBadge.textContent = '⏳ กำลังทำงาน...';
        secBadge.className = 'badge badge-processing';
      } else {
        secBadge.textContent = 'Online';
        secBadge.className = 'badge badge-online';
      }
    }
  } catch (err) {
    console.error('Failed to update agent statuses:', err);
  }
}

// Start polling for agent status every 1.5 seconds
setInterval(updateAgentStatuses, 1500);

// ─── Authentication & Security Guard ─────────────────────────
function getEnterpriseToken() {
  return localStorage.getItem('ai_enterprise_token') || sessionStorage.getItem('ai_enterprise_token');
}

function checkEnterpriseAuth() {
  const token = getEnterpriseToken();
  const loginScreen = document.getElementById('login-screen');
  if (!token) {
    if (loginScreen) {
      loginScreen.style.display = 'flex';
    }
    return false;
  }
  fetch('/api/auth/verify', {
    headers: { 'Authorization': `Bearer ${token}` }
  }).then(res => {
    if (!res.ok) {
      localStorage.removeItem('ai_enterprise_token');
      sessionStorage.removeItem('ai_enterprise_token');
      if (loginScreen) loginScreen.style.display = 'flex';
    } else {
      if (loginScreen) loginScreen.style.display = 'none';
    }
  }).catch(() => {
    // If server temporarily unreachable, keep session alive
  });
  return true;
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const userEl = document.getElementById('login-username');
  const passEl = document.getElementById('login-password');
  const remEl = document.getElementById('login-remember');
  const btnEl = document.getElementById('login-btn');
  const errEl = document.getElementById('login-error');
  const errText = document.getElementById('login-error-text');

  if (!userEl || !passEl) return;
  const username = userEl.value.trim();
  const password = passEl.value.trim();

  if (errEl) errEl.style.display = 'none';
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.innerHTML = '<span>⏳ กำลังตรวจสอบ...</span>';
  }

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง');
    }

    if (remEl && remEl.checked) {
      localStorage.setItem('ai_enterprise_token', data.token);
      localStorage.setItem('ai_enterprise_owner', data.owner_name || username);
    } else {
      sessionStorage.setItem('ai_enterprise_token', data.token);
      sessionStorage.setItem('ai_enterprise_owner', data.owner_name || username);
    }

    const loginScreen = document.getElementById('login-screen');
    if (loginScreen) {
      loginScreen.style.display = 'none';
    }

    if (typeof toast === 'function') {
      toast(`🎉 ยินดีต้อนรับคุณ ${data.owner_name || username} เข้าสู่ระบบ AI Enterprise`, 'success');
    }

    // Refresh dashboard
    loadDashboard();

  } catch (err) {
    if (errEl && errText) {
      errText.textContent = err.message;
      errEl.style.display = 'flex';
    }
  } finally {
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.innerHTML = '<span>เข้าสู่ระบบองค์กร</span><span>→</span>';
    }
  }
}

function logoutEnterprise() {
  if (!confirm('ต้องการออกจากระบบ AI Enterprise หรือไม่?')) return;
  localStorage.removeItem('ai_enterprise_token');
  sessionStorage.removeItem('ai_enterprise_token');
  const loginScreen = document.getElementById('login-screen');
  if (loginScreen) {
    loginScreen.style.display = 'flex';
    const passInput = document.getElementById('login-password');
    if (passInput) passInput.value = '';
  }
  if (typeof toast === 'function') {
    toast('🔒 ออกจากระบบเรียบร้อยแล้ว', 'info');
  }
}

function togglePasswordVisibility(inputId) {
  const el = document.getElementById(inputId);
  if (!el) return;
  el.type = el.type === 'password' ? 'text' : 'password';
}

async function changeEnterprisePassword() {
  const currentPass = document.getElementById('sec-current-pass')?.value;
  const newPass = document.getElementById('sec-new-pass')?.value;
  const statusEl = document.getElementById('save-status-security');

  if (!currentPass || !newPass) {
    if (typeof toast === 'function') toast('กรุณากรอกรหัสผ่านปัจจุบันและรหัสผ่านใหม่', 'warning');
    return;
  }

  const token = getEnterpriseToken();
  try {
    const res = await fetch('/api/auth/change-password', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ current_password: currentPass, new_password: newPass })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'เปลี่ยนรหัสผ่านไม่สำเร็จ');

    if (statusEl) {
      statusEl.textContent = '✅ ' + data.message;
      statusEl.style.color = '#34d399';
    }
    if (typeof toast === 'function') toast('✅ เปลี่ยนรหัสผ่านเข้าสู่ระบบเรียบร้อยแล้ว', 'success');
    document.getElementById('sec-current-pass').value = '';
    document.getElementById('sec-new-pass').value = '';
  } catch (err) {
    if (statusEl) {
      statusEl.textContent = '❌ ' + err.message;
      statusEl.style.color = '#f87171';
    }
    if (typeof toast === 'function') toast(err.message, 'error');
  }
}

// ─── Company Directives & Operating Policies ─────────────────
let _cachedDirectives = null;

async function loadDirectivesPage() {
  try {
    const [res, agents] = await Promise.all([
      fetch('/api/company/directives'),
      apiGet('/api/agents').catch(() => [])
    ]);
    if (!res.ok) throw new Error(await res.text());
    _cachedDirectives = await res.json();
    populateDirectivesForm(_cachedDirectives);
    renderDirectivesActiveDepts(agents || []);
  } catch (err) {
    console.error('Failed to load directives:', err);
    if (typeof toast === 'function') toast('เกิดข้อผิดพลาดในการโหลดนโยบายบริษัท', 'error');
  }
}

function renderDirectivesActiveDepts(agents) {
  const container = document.getElementById('dir-active-depts-container');
  if (!container) return;
  if (!agents || !agents.length) {
    container.innerHTML = '<div class="empty-state">ยังไม่มีข้อมูลทีมงาน</div>';
    return;
  }
  container.innerHTML = agents.map((a, idx) => {
    const isSecretary = a.id === '01_secretary';
    const icon = isSecretary ? '🗂️' : '🏢';
    const pm = a.pm_name || a.name;
    return `
      <div style="background:rgba(255,255,255,0.03); padding:10px 14px; border-radius:6px; border:1px solid var(--border); display:flex; align-items:center; gap:8px;">
        <span>${icon}</span>
        <div>
          <div style="font-weight:600; font-size:13px; color:var(--text-primary);">${idx + 1}. <b>${escHtml(a.name)}</b></div>
          <div style="font-size:11px; color:var(--text-muted);">ผู้รับผิดชอบ: <span style="color:#60a5fa;">${escHtml(pm)}</span> • โมเดล: <code>${escHtml(a.model || 'gemini-1.5-flash')}</code></div>
        </div>
      </div>
    `;
  }).join('');
}

function populateDirectivesForm(d) {
  if (!d) return;
  const wh = d.working_hours || {};
  const sd = d.strategic_direction || {};
  const pol = d.policies || {};
  const cm = d.company_model || {};

  const setVal = (id, val) => {
    const el = document.getElementById(id);
    if (el && val !== undefined) el.value = val;
  };

  setVal('dir-hours-mode', wh.mode || 'autonomous_24_7');
  setVal('dir-hours-days', wh.work_days || 'ทุกวัน (จันทร์ - อาทิตย์)');
  setVal('dir-hours-morning', wh.morning_briefing_time || '08:30');
  setVal('dir-hours-evening', wh.evening_summary_time || '18:00');
  setVal('dir-hours-off', wh.off_hours_behavior || '');

  setVal('dir-vision', sd.vision || '');
  setVal('dir-focus', sd.primary_focus || '');
  setVal('dir-goals', sd.quarterly_goals || '');
  setVal('dir-audience', sd.target_audience || '');
  setVal('dir-tone', sd.brand_tone || '');

  setVal('dir-pol-hitl', pol.hitl_rule || '');
  setVal('dir-pol-token', pol.token_cost_policy || '');
  setVal('dir-pol-qa', pol.quality_assurance || '');
  setVal('dir-pol-sec', pol.security_privacy || '');

  setVal('dir-model-type', cm.model_type || '');
  setVal('dir-model-leader', cm.supreme_leader || '');
  setVal('dir-model-scaling', cm.workforce_scaling || '');
}

function switchDirectivesTab(tab) {
  document.querySelectorAll('.directives-tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });
  document.querySelectorAll('.directives-section').forEach(sec => {
    sec.classList.toggle('active', sec.id === `directives-sec-${tab}`);
  });
}

async function saveDirectivesChanges() {
  const saveBtn = document.getElementById('btn-save-directives');
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span>⏳ กำลังบันทึก...</span>';
  }

  const payload = {
    working_hours: {
      mode: document.getElementById('dir-hours-mode')?.value,
      work_days: document.getElementById('dir-hours-days')?.value,
      morning_briefing_time: document.getElementById('dir-hours-morning')?.value,
      evening_summary_time: document.getElementById('dir-hours-evening')?.value,
      off_hours_behavior: document.getElementById('dir-hours-off')?.value
    },
    strategic_direction: {
      vision: document.getElementById('dir-vision')?.value,
      primary_focus: document.getElementById('dir-focus')?.value,
      quarterly_goals: document.getElementById('dir-goals')?.value,
      target_audience: document.getElementById('dir-audience')?.value,
      brand_tone: document.getElementById('dir-tone')?.value
    },
    policies: {
      hitl_rule: document.getElementById('dir-pol-hitl')?.value,
      token_cost_policy: document.getElementById('dir-pol-token')?.value,
      quality_assurance: document.getElementById('dir-pol-qa')?.value,
      security_privacy: document.getElementById('dir-pol-sec')?.value
    },
    company_model: {
      model_type: document.getElementById('dir-model-type')?.value,
      supreme_leader: document.getElementById('dir-model-leader')?.value,
      workforce_scaling: document.getElementById('dir-model-scaling')?.value
    }
  };

  try {
    const res = await fetch('/api/company/directives', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'บันทึกไม่สำเร็จ');

    _cachedDirectives = data.directives;
    if (typeof toast === 'function') {
      toast('🎉 บันทึกเวลาทำงาน ทิศทาง และนโยบายบริษัทเรียบร้อยแล้ว (ซิงค์สู่ AI ทั้ง 6 แผนกแล้ว)', 'success');
    }
  } catch (err) {
    console.error('Failed to save directives:', err);
    if (typeof toast === 'function') toast(`เกิดข้อผิดพลาดในการบันทึก: ${err.message}`, 'error');
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.innerHTML = '<span>💾 บันทึกทิศทางและนโยบาย</span>';
    }
  }
}

// Global exports
window.handleLoginSubmit = handleLoginSubmit;
window.logoutEnterprise = logoutEnterprise;
window.togglePasswordVisibility = togglePasswordVisibility;
window.changeEnterprisePassword = changeEnterprisePassword;
window.loadDirectivesPage = loadDirectivesPage;
window.switchDirectivesTab = switchDirectivesTab;
window.saveDirectivesChanges = saveDirectivesChanges;

// ─── Company Shift Controller (Start / End Work) ─────────────
let _companyShiftState = 'active';

async function initCompanyShift() {
  try {
    const res = await fetch('/api/company/shift');
    if (!res.ok) return;
    const data = await res.json();
    _companyShiftState = data.status || 'active';
    renderShiftUI(_companyShiftState);
  } catch (err) {
    console.error('Failed to init company shift:', err);
  }
}

function renderShiftUI(status) {
  const indicator = document.getElementById('shift-indicator');
  const btn = document.getElementById('btn-toggle-shift');
  if (!indicator || !btn) return;

  if (status === 'active') {
    indicator.className = 'shift-indicator on';
    indicator.innerHTML = '🟢 เปิดทำการ';
    btn.className = 'btn btn-sm btn-shift-end';
    btn.innerHTML = '<span>⏹️ เลิกงาน</span>';
    btn.title = 'กดเมื่อเลิกงานประจำวัน เพื่อให้อิงฟ้าสรุปผลงาน EOD และเข้าสู่โหมดพักผ่อน';
  } else {
    indicator.className = 'shift-indicator off';
    indicator.innerHTML = '🌙 เลิกงาน';
    btn.className = 'btn btn-sm btn-shift-start';
    btn.innerHTML = '<span>🚀 เริ่มงาน</span>';
    btn.title = 'กดเมื่อเริ่มงาน เพื่อปลุกทีมงาน AI ทุกแผนกและให้อิงฟ้าส่งสรุปเช้า';
  }
}

async function toggleCompanyShift() {
  const isCurrentlyActive = _companyShiftState === 'active';
  const action = isCurrentlyActive ? 'end' : 'start';

  const confirmMsg = isCurrentlyActive
    ? 'ต้องการกด "เลิกงานประจำวัน" หรือไม่?\n\n(เลขาอิงฟ้าจะรวบรวมผลงานสรุป EOD ส่งเข้า Telegram และให้ทีมงาน AI เข้าสู่โหมดพักผ่อน)'
    : 'ต้องการกด "เริ่มงานประจำวัน" หรือไม่?\n\n(ทีมงาน AI ทุกแผนกจะตื่นพร้อมทำงาน และเลขาอิงฟ้าจะส่งรายงานสรุปเช้าเข้า Telegram)';

  if (!confirm(confirmMsg)) return;

  const btn = document.getElementById('btn-toggle-shift');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span>⏳ กำลังประมวลผล...</span>';
  }

  try {
    const res = await fetch(`/api/company/shift/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'ไม่สามารถเปลี่ยนสถานะกะทำงานได้');

    _companyShiftState = data.status;
    renderShiftUI(_companyShiftState);

    if (typeof toast === 'function') {
      toast(data.message, isCurrentlyActive ? 'info' : 'success');
    }

    // Refresh simulation state & agent statuses
    if (typeof fetchSimulationState === 'function') fetchSimulationState();
    if (typeof updateAgentStatuses === 'function') updateAgentStatuses();

  } catch (err) {
    console.error('Failed to toggle shift:', err);
    if (typeof toast === 'function') toast(`เกิดข้อผิดพลาด: ${err.message}`, 'error');
  } finally {
    if (btn) btn.disabled = false;
  }
}

window.initCompanyShift = initCompanyShift;
window.toggleCompanyShift = toggleCompanyShift;


