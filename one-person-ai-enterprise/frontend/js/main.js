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
  routeFromHash();
  startClock();
  fetchHealthCheck();
  connectLogWS();

  window.addEventListener('hashchange', routeFromHash);
  window.addEventListener('resize', () => {
    if (window.innerWidth < 780) collapseSidebar();
  });
});

// ─── Routing ──────────────────────────────────────────────────
const PAGES = {
  dashboard: { title: 'ภาพรวมระบบ', sub: 'One-Person AI Enterprise Platform', load: loadDashboard },
  boardroom: { title: 'ห้องประชุมผู้บริหาร', sub: 'กำหนดนโยบาย สั่งงาน ประชุม Director', load: loadBoardroom },
  teams:     { title: 'ทีมปฏิบัติการ', sub: 'จัดการทีม Agent และ PM Bots', load: loadTeams },
  logs:      { title: 'Logs การทำงาน', sub: 'ติดตาม Log ระบบ Real-time', load: loadLogs },
  settings:  { title: 'ตั้งค่าระบบ', sub: 'API Keys, Bot Token, การเชื่อมต่อ', load: loadSettings },
};

function routeFromHash() {
  const hash = location.hash.replace('#/', '') || 'dashboard';
  const page = PAGES[hash] ? hash : 'dashboard';
  activatePage(page);
}

function navigateTo(page) {
  location.hash = '#/' + page;
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
//  PAGE: DASHBOARD
// ══════════════════════════════════════════════════════════════
async function loadDashboard() {
  try {
    const [agents, rooms] = await Promise.all([
      apiGet('/api/agents'),
      apiGet('/api/telegram/rooms'),
    ]);
    allAgents = agents;
    allRooms  = rooms;

    // Stats
    const depts = new Set(agents.map(a => a.department)).size;
    document.getElementById('stat-agents').textContent = agents.length;
    document.getElementById('stat-depts').textContent  = depts;
    document.getElementById('stat-logs').textContent   = allLogs.length;
    document.getElementById('stat-telegram').textContent = rooms.bot_configured ? '✓ เชื่อมต่อ' : '✗ ยังไม่ตั้งค่า';
    document.getElementById('badge-teams').textContent = depts;

    // Quick teams
    renderQuickTeams(rooms);

    // Log preview
    updateDashboardLogPreview();
  } catch (err) {
    console.error(err);
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
    const tokenBadge  = token
      ? `<span class="team-token-badge ok">🤖 Bot OK</span>`
      : `<span class="team-token-badge missing">⚠️ ยังไม่มี Token</span>`;

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
      <button class="btn btn-sm btn-primary" onclick="openSecretaryChat()">💬 คุยกับอิงฟ้า</button>
      <button class="btn btn-sm" onclick="openCreateAgentForDept('${deptId}')">＋ Agent</button>
    ` : `
      <button class="btn btn-sm btn-primary" onclick="openDirectCommandModal('${deptId}', '${escHtml(name)}')">💬 สั่งงาน</button>
      <button class="btn btn-sm" onclick="openCreateAgentForDept('${deptId}')">＋ Agent</button>
      ${!token ? `<button class="btn btn-sm" onclick="setTokenForTeam('${deptId}', '${escHtml(name)}')">🔑 ตั้งค่า Token</button>` : ''}
      <button class="btn btn-sm btn-danger" onclick="deleteTeam('${deptId}', '${escHtml(name)}')">🗑️</button>
    `;

    return `
      <div class="team-card" id="tc-${deptId}">
        <div class="team-card-head">
          <div class="team-avatar">${avatarEmoji}</div>
          <div class="team-info">
            <div class="team-name">${escHtml(name)}</div>
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
  } catch (err) {
    toast('ลบทีมไม่สำเร็จ: ' + err.message, 'error');
  }
}

// ─── Create Agent Modal ────────────────────────────────────────
function openCreateAgentModal() {
  document.getElementById('ca-edit-id').value = '';
  document.getElementById('agent-modal-title').textContent = '🤖 สร้าง Agent ใหม่';
  document.getElementById('ca-name').value = '';
  document.getElementById('ca-identity').value = '';
  document.getElementById('ca-skill').value = '';
  document.getElementById('ca-temp').value = 0.5;
  document.getElementById('ca-temp-val').textContent = '0.5';
  
  // เรียกใช้ dynamic model list
  renderModelSelect('ca-model', 'gemini-1.5-flash');
  
  updateAgentDeptSelect(allRooms);
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
    
    // เรียกใช้ dynamic model list
    renderModelSelect('ca-model', a.model);
    
    document.getElementById('ca-temp').value = a.temperature;
    document.getElementById('ca-temp-val').textContent = a.temperature;
    document.getElementById('ca-identity').value = a.identity || '';
    document.getElementById('ca-skill').value    = a.skill    || '';
    updateAgentDeptSelect(allRooms);
    document.getElementById('ca-dept').value = a.department;
    openModal('modal-create-agent');
  } catch (err) {
    toast('โหลดข้อมูล Agent ไม่สำเร็จ', 'error');
  }
}

async function submitAgent() {
  const editId = document.getElementById('ca-edit-id').value;
  const data = {
    name:       document.getElementById('ca-name').value.trim(),
    department: document.getElementById('ca-dept').value,
    model:      document.getElementById('ca-model').value,
    temperature: parseFloat(document.getElementById('ca-temp').value),
    identity:   document.getElementById('ca-identity').value.trim(),
    skill:      document.getElementById('ca-skill').value.trim(),
  };

  if (!data.name || !data.identity || !data.skill) {
    toast('กรุณากรอกข้อมูลให้ครบทุกช่อง (*)', 'warning'); return;
  }

  const btn = document.querySelector('#modal-create-agent .btn-primary');
  btn.disabled = true; btn.textContent = '⏳ กำลังบันทึก...';

  try {
    if (editId) {
      await apiPut(`/api/agents/${editId}`, data);
      toast(`✅ แก้ไข Agent "${data.name}" สำเร็จ!`, 'success');
    } else {
      await apiPost('/api/agents', data);
      toast(`✅ สร้าง Agent "${data.name}" สำเร็จ!`, 'success');
    }
    closeModal('modal-create-agent');
    await loadTeams();
    await loadDashboard();
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

let allAvailableModels = [];

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

    // Show masked placeholder for sensitive fields
    setMaskedInput('s-gemini-key', s.gemini_configured, s.gemini_api_key, 's-gemini-status');
    setMaskedInput('s-claude-key', s.anthropic_configured, s.anthropic_api_key, 's-claude-status');
    setMaskedInput('s-tg-token',   s.telegram_configured,  s.telegram_bot_token, 's-tg-token-status');

    // Plain text fields — fill directly
    document.getElementById('s-direct-chat').value = s.telegram_owner_direct_chat_id || '';
    document.getElementById('s-gemini-fallbacks').value = s.gemini_fallback_models || '';
    document.getElementById('s-available-models').value = s.available_models || '';

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

    // PM Tokens
    renderPmTokens(rooms.department_rooms || {});
  } catch (err) {
    console.error('[loadSettings]', err);
    toast('โหลดการตั้งค่าไม่สำเร็จ: ' + err.message, 'error');
  }
}

function renderModelSelect(selectId, selectedValue = '') {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  
  sel.innerHTML = allAvailableModels.map(m => {
    // ใส่ emoji แนะนำความเร็ว/ความฉลาดเพื่อความสวยงาม
    let emoji = '🤖';
    if (m.includes('flash')) emoji = '⚡';
    else if (m.includes('pro')) emoji = '🧠';
    else if (m.includes('sonnet')) emoji = '🎭';
    
    return `<option value="${m}">${emoji} ${m}</option>`;
  }).join('');
  
  if (selectedValue) {
    sel.value = selectedValue;
  }
}

function setMaskedInput(inputId, isConfigured, maskedValue, badgeId) {
  const input = document.getElementById(inputId);
  const badge = document.getElementById(badgeId);
  if (!input || !badge) return;

  // Clear actual value (user must re-type to change)
  input.value = '';

  if (isConfigured) {
    // Show last 6 chars hint in placeholder
    const hint = maskedValue ? maskedValue.replace(/•+/, '').slice(-6) : '...';
    input.placeholder = `ตั้งค่าแล้ว (••••••${hint}) — พิมพ์ใหม่เพื่อเปลี่ยน`;
    badge.className   = 'config-badge ok';
    badge.textContent = '✓ ตั้งค่าแล้ว';
  } else {
    input.placeholder = inputId === 's-gemini-key' ? 'AIzaSy...'
      : inputId === 's-claude-key' ? 'sk-ant-...'
      : '123456789:ABCdefGHI...';
    badge.className   = 'config-badge warn';
    badge.textContent = '✗ ยังไม่ตั้งค่า';
  }
}

function renderPmTokens(depts) {
  const el = document.getElementById('pm-tokens-container');
  const deptKeys = Object.keys(depts).filter(k => k !== '01_secretary');
  if (deptKeys.length === 0) {
    el.innerHTML = `<div class="empty-state">ยังไม่มีทีม — ไปที่ <a href="#/teams" onclick="navigateTo('teams')">ทีมปฏิบัติการ</a> เพื่อสร้างทีมค่ะ</div>`;
    return;
  }

  el.innerHTML = deptKeys.map(id => {
    const d = depts[id];
    const hasToken = !!d.bot_token;
    const tokenHint = hasToken ? d.bot_token.replace(/•+/, '').slice(-6) : '';
    return `
      <div class="pm-token-item">
        <div class="pm-token-label">
          <span class="pm-token-name">🤖 PM ทีม ${escHtml(d.name)}</span>
          <span class="config-badge ${hasToken ? 'ok' : 'warn'}">${hasToken ? '✓ ตั้งค่าแล้ว' : '✗ ยังไม่มี Token'}</span>
        </div>
        <div class="input-row">
          <input type="password" class="form-input mono" id="pm-token-${id}"
            placeholder="${hasToken ? `ตั้งค่าแล้ว (••••••${tokenHint}) — พิมพ์ใหม่เพื่อเปลี่ยน` : 'Bot Token จาก @BotFather...'}" autocomplete="off" />
          <span class="form-hint" style="flex-shrink:0">PM: ${escHtml(d.pm_name || '—')}</span>
        </div>
      </div>`;
  }).join('');
}

// ─── Helper: call PUT /api/settings and show save result ──────
async function _doSaveSettings(body, btnId, statusId, btnLabel) {
  const btn    = document.getElementById(btnId);
  const status = document.getElementById(statusId);
  if (btn) { btn.disabled = true; btn.textContent = '⏳ กำลังบันทึก...'; }
  if (status) status.textContent = '';

  // Remove any empty or untouched fields
  const cleaned = {};
  Object.entries(body).forEach(([k, v]) => {
    if (v !== null && v !== undefined && String(v).trim() !== '') {
      cleaned[k] = v;
    }
  });

  if (Object.keys(cleaned).length === 0) {
    toast('ไม่มีข้อมูลใหม่ให้บันทึก — กรุณาพิมพ์ค่าใหม่ก่อนค่ะ', 'warning');
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
  const body = {
    gemini_api_key:         document.getElementById('s-gemini-key').value.trim() || null,
    anthropic_api_key:      document.getElementById('s-claude-key').value.trim() || null,
    default_model:          document.getElementById('s-default-model').value || null,
    gemini_fallback_models: document.getElementById('s-gemini-fallbacks').value.trim() || null,
    available_models:       document.getElementById('s-available-models').value.trim() || null,
  };
  // Remove nulls
  Object.keys(body).forEach(k => { if (!body[k]) delete body[k]; });
  await _doSaveSettings(body, 'btn-save-llm', 'save-status-llm', '💾 บันทึก LLM Keys');
}

async function saveTelegramSection() {
  const body = {
    telegram_bot_token:            document.getElementById('s-tg-token').value.trim() || null,
    telegram_owner_direct_chat_id: document.getElementById('s-direct-chat').value.trim() || null,
  };
  Object.keys(body).forEach(k => { if (!body[k]) delete body[k]; });
  await _doSaveSettings(body, 'btn-save-tg', 'save-status-tg', '💾 บันทึก Telegram Settings');
}

async function savePmTokens() {
  const btn    = document.getElementById('btn-save-pm');
  const status = document.getElementById('save-status-pm');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ กำลังบันทึก...'; }
  if (status) status.textContent = '';

  const pmInputs = document.querySelectorAll('[id^="pm-token-"]');
  const promises = [];
  let count = 0;

  pmInputs.forEach(inp => {
    const val = inp.value.trim();
    if (val) {  // user actually typed something
      count++;
      const deptId = inp.id.replace('pm-token-', '');
      const room = (allRooms.department_rooms || {})[deptId];
      if (room) {
        promises.push(
          apiPost('/api/telegram/rooms', {
            name: room.name, pm_name: room.pm_name || '', id: deptId, bot_token: val
          }).catch(e => ({ error: e.message }))
        );
      }
    }
  });

  if (count === 0) {
    toast('ไม่มี Token ใหม่ให้บันทึก — กรุณาพิมพ์ Token ในช่องที่ต้องการเปลี่ยนค่ะ', 'warning');
    if (btn) { btn.disabled = false; btn.textContent = '💾 บันทึก PM Bot Tokens'; }
    return;
  }

  try {
    await Promise.all(promises);
    toast(`✅ บันทึก PM Bot Token สำเร็จ ${count} ทีม!`, 'success');
    if (status) { status.textContent = `✅ บันทึก ${count} ทีม`; setTimeout(() => { if (status) status.textContent = ''; }, 3000); }
    await loadSettings();
  } catch (err) {
    toast('บันทึก PM Token ไม่สำเร็จ: ' + err.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '💾 บันทึก PM Bot Tokens'; }
  }
}

// ─── Save All (runs all 3 sections) ──────────────────────────
async function saveSettings() {
  const btn    = document.getElementById('btn-save');
  const status = document.getElementById('save-status');
  btn.disabled = true; btn.textContent = '⏳ กำลังบันทึกทั้งหมด...';
  status.textContent = '';

  const body = {
    gemini_api_key:                document.getElementById('s-gemini-key').value.trim() || null,
    anthropic_api_key:             document.getElementById('s-claude-key').value.trim() || null,
    default_model:                 document.getElementById('s-default-model').value || null,
    gemini_fallback_models:        document.getElementById('s-gemini-fallbacks').value.trim() || null,
    available_models:              document.getElementById('s-available-models').value.trim() || null,
    telegram_bot_token:            document.getElementById('s-tg-token').value.trim() || null,
    telegram_owner_direct_chat_id: document.getElementById('s-direct-chat').value.trim() || null,
  };
  // Remove nulls (only send fields user actually typed)
  Object.keys(body).forEach(k => { if (!body[k]) delete body[k]; });

  // PM tokens
  const pmInputs = document.querySelectorAll('[id^="pm-token-"]');
  const pmPromises = [];
  pmInputs.forEach(inp => {
    const val = inp.value.trim();
    if (val) {
      const deptId = inp.id.replace('pm-token-', '');
      const room = (allRooms.department_rooms || {})[deptId];
      if (room) {
        pmPromises.push(
          apiPost('/api/telegram/rooms', {
            name: room.name, pm_name: room.pm_name || '', id: deptId, bot_token: val
          }).catch(() => {})
        );
      }
    }
  });

  const hasMainSettings = Object.keys(body).length > 0;
  const hasPmTokens     = pmPromises.length > 0;

  if (!hasMainSettings && !hasPmTokens) {
    toast('ไม่มีข้อมูลใหม่ให้บันทึก — กรุณาพิมพ์ค่าใหม่ในช่องที่ต้องการก่อนค่ะ', 'warning');
    btn.disabled = false; btn.textContent = '💾 บันทึกทั้งหมด';
    return;
  }

  try {
    const tasks = [];
    if (hasMainSettings) tasks.push(apiPut('/api/settings', body));
    tasks.push(...pmPromises);
    await Promise.all(tasks);
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
