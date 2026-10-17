/* ═══════════════════════════════════════════════════════════════
   simulation.js — Real-Time Visual Kanban Engine & HITL Approvals
   One-Person AI Enterprise
   ═══════════════════════════════════════════════════════════════ */

'use strict';

let simWs = null;
let currentSimState = {
  agents: [],
  tasks: [],
  pending_confirmations: [],
  active_tasks: [],
  confirmed_tasks: [],
  pending_hires: [],
  notifications: []
};

let activeDeliverableTaskId = null;

// ─── 6 Departments Configuration & Capabilities ─────────────────
const ENTERPRISE_DEPARTMENTS = {
  '01_secretary': {
    id: '01_secretary',
    name: 'สำนักเลขาธิการ & CKO',
    pm: 'อิงฟ้า (เลขา AI)',
    avatar: '🗂️',
    role: 'Executive Secretary & CKO',
    color: '#38bdf8',
    glow: 'rgba(56, 189, 248, 0.25)',
    btnBorder: 'rgba(56, 189, 248, 0.4)',
    btnBg: 'linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(14, 165, 233, 0.35))',
    btnHover: 'linear-gradient(135deg, rgba(56, 189, 248, 0.4), rgba(14, 165, 233, 0.6))',
    btnColor: '#bae6fd',
    skills: 'วางแผนกลยุทธ์องค์กร, ประสานงานข้ามทีม, สรุปการประชุม, จัดการคลังความรู้',
    preset: 'secretary',
    quickAction: '🌅 สรุปงานวันนี้',
    quickPrompt: 'จัดทำรายงานสรุปความคืบหน้าของทุกแผนก และอัปเดตลง company_memory.md',
    templates: [
      'จัดทำรายงานสรุปความคืบหน้าของทุกแผนก และอัปเดตลง company_memory.md',
      'เปิดวาระประชุมติดตามความคืบหน้าระบบและแผนการตลาดประจำสัปดาห์',
      'วิเคราะห์และวางโครงสร้างการแบ่งงานระหว่างทีม Dev และ Marketing สำหรับโปรเจกต์ใหม่'
    ]
  },
  '03_developer': {
    id: '03_developer',
    name: 'ฝ่ายพัฒนาระบบซอฟต์แวร์',
    pm: 'บิ๊นท์ (Lead Dev)',
    avatar: '💻',
    role: 'Lead Software & Systems Dev',
    color: '#818cf8',
    glow: 'rgba(129, 140, 248, 0.25)',
    btnBorder: 'rgba(129, 140, 248, 0.4)',
    btnBg: 'linear-gradient(135deg, rgba(129, 140, 248, 0.2), rgba(99, 102, 241, 0.35))',
    btnHover: 'linear-gradient(135deg, rgba(129, 140, 248, 0.4), rgba(99, 102, 241, 0.6))',
    btnColor: '#c7d2fe',
    skills: 'Full-Stack Web, REST API, Database, Authentication, Automation Scripts',
    preset: 'systems_dev',
    quickAction: '🔑 สร้าง API + Auth',
    quickPrompt: 'พัฒนาระบบ Backend REST API พร้อม JWT Authentication และ Unit Tests',
    templates: [
      'พัฒนาระบบ Backend REST API พร้อม JWT Authentication และ Unit Tests',
      'ออกแบบและสร้าง Microservice Database พร้อมระบบ Rate Limiting',
      'พัฒนา Webhook สำหรับเชื่อมต่อระบบชำระเงินและแจ้งเตือนอัตโนมัติ'
    ]
  },
  '02_การตลาด_ai': {
    id: '02_การตลาด_ai',
    name: 'ฝ่ายการตลาด & Social Content',
    pm: 'ลิซ่า (Content Lead)',
    avatar: '📣',
    role: 'Head of Marketing & Content',
    color: '#f472b6',
    glow: 'rgba(244, 114, 182, 0.25)',
    btnBorder: 'rgba(244, 114, 182, 0.4)',
    btnBg: 'linear-gradient(135deg, rgba(244, 114, 182, 0.2), rgba(236, 72, 153, 0.35))',
    btnHover: 'linear-gradient(135deg, rgba(244, 114, 182, 0.4), rgba(236, 72, 153, 0.6))',
    btnColor: '#fbcfe8',
    skills: 'สคริปต์วิดีโอสั้น TikTok/Reels, บทความ Facebook/LinkedIn, AI Visual Prompts',
    preset: 'social_content',
    quickAction: '🎬 คลิป TikTok 45 วิ',
    quickPrompt: 'สร้าง Content Social Media: เปิดตัว One-Person AI Enterprise 100% (TikTok & Facebook)',
    templates: [
      'สร้าง Content Social Media: เปิดตัว One-Person AI Enterprise 100% (TikTok & Facebook)',
      'เขียนสคริปต์วิดีโอสั้น TikTok 3 คลิป เจาะกลุ่มคนทำธุรกิจยุคใหม่',
      'เขียนบทความเจาะลึกเบื้องหลังระบบ AI สำหรับโพสต์ลง Facebook Page และ LinkedIn'
    ]
  },
  '06_devops': {
    id: '06_devops',
    name: 'ฝ่ายวิศวกรรมคลาวด์ & DevOps',
    pm: 'ก้อง (Cloud DevOps)',
    avatar: '⚡',
    role: 'Cloud DevOps & Infra Specialist',
    color: '#fbbf24',
    glow: 'rgba(251, 191, 36, 0.25)',
    btnBorder: 'rgba(251, 191, 36, 0.4)',
    btnBg: 'linear-gradient(135deg, rgba(251, 191, 36, 0.2), rgba(245, 158, 11, 0.35))',
    btnHover: 'linear-gradient(135deg, rgba(251, 191, 36, 0.4), rgba(245, 158, 11, 0.6))',
    btnColor: '#fde68a',
    skills: 'Container Docker, CI/CD Pipeline, Nginx Reverse Proxy, Server Uptime 99.99%',
    preset: 'devops',
    quickAction: '🐳 เซ็ต Docker & CI/CD',
    quickPrompt: 'วางระบบ Container Docker และ CI/CD Pipeline อัตโนมัติ',
    templates: [
      'วางระบบ Container Docker และ CI/CD Pipeline อัตโนมัติ',
      'เขียน docker-compose สำหรับรัน FastAPI, Postgres, Redis และ Nginx SSL',
      'ตรวจสอบความปลอดภัยของเซิร์ฟเวอร์ และตั้งค่าระบบ Automated Healthcheck'
    ]
  },
  '04_data_analyst': {
    id: '04_data_analyst',
    name: 'ฝ่ายตรวจสอบคุณภาพ & Data',
    pm: 'มุก (QA Analyst)',
    avatar: '📊',
    role: 'Senior QA & Data Analyst',
    color: '#34d399',
    glow: 'rgba(52, 211, 153, 0.25)',
    btnBorder: 'rgba(52, 211, 153, 0.4)',
    btnBg: 'linear-gradient(135deg, rgba(52, 211, 153, 0.2), rgba(16, 185, 129, 0.35))',
    btnHover: 'linear-gradient(135deg, rgba(52, 211, 153, 0.4), rgba(16, 185, 129, 0.6))',
    btnColor: '#a7f3d0',
    skills: 'QA Code Review, Funnel Analytics, สแกนช่องโหว่ความปลอดภัย, สถิติผู้ใช้งาน',
    preset: 'data_analyst',
    quickAction: '📈 วิเคราะห์ Funnel',
    quickPrompt: 'วิเคราะห์ Conversion Funnel และสแกนคอขวดของระบบ',
    templates: [
      'วิเคราะห์ Conversion Funnel และสแกนคอขวดของระบบ',
      'รัน Security Audit และ Code Review ตรวจหาช่องโหว่ SQL Injection และ Auth Leaks',
      'วิเคราะห์พฤติกรรมผู้ใช้งานเพื่อหาจุดหลุดสูงสุด 3 อันดับแรกในระบบชำระเงิน'
    ]
  },
  '05_accounting': {
    id: '05_accounting',
    name: 'ฝ่ายการเงิน & ต้นทุน Cloud',
    pm: 'พลอย (Finance)',
    avatar: '💰',
    role: 'Finance & Cost Controller',
    color: '#a78bfa',
    glow: 'rgba(167, 139, 250, 0.25)',
    btnBorder: 'rgba(167, 139, 250, 0.4)',
    btnBg: 'linear-gradient(135deg, rgba(167, 139, 250, 0.2), rgba(139, 92, 246, 0.35))',
    btnHover: 'linear-gradient(135deg, rgba(167, 139, 250, 0.4), rgba(139, 92, 246, 0.6))',
    btnColor: '#ddd6fe',
    skills: 'สรุปค่าใช้จ่าย API Token, ควบคุมงบประมาณ Cloud, คำนวณ ROI และจุดคุ้มทุน',
    preset: 'accounting',
    quickAction: '💵 สรุปค่า Token',
    quickPrompt: 'สรุปยอดการใช้งาน AI Tokens และควบคุมงบประมาณ Cloud รายเดือน',
    templates: [
      'สรุปยอดการใช้งาน AI Tokens และควบคุมงบประมาณ Cloud รายเดือน',
      'คำนวณต้นทุนต่อผู้ใช้งาน (Cost per Active User) และวิเคราะห์จุดคุ้มทุน ROI',
      'วางแผนกลยุทธ์ Prompt Caching เพื่อลดค่าใช้จ่าย API รายเดือนลง 35%'
    ]
  }
};

// ─── Network & Toast Helpers ──────────────────────────────────
async function simGet(url) {
  if (typeof apiGet === 'function') return apiGet(url);
  const r = await fetch(url);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function simPost(url, body) {
  if (typeof apiPost === 'function') return apiPost(url, body);
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function simToast(msg, type = 'info') {
  if (typeof toast === 'function') {
    toast(msg, type);
  } else {
    console.log(`[Toast ${type}] ${msg}`);
  }
}

// ─── Initialize Engine ─────────────────────────────────────────
function initSimulation() {
  fetchSimulationState();
  if (!simWs || simWs.readyState !== WebSocket.OPEN) {
    connectSimulationWS();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  fetchSimulationState();
  connectSimulationWS();
});

async function fetchSimulationState() {
  try {
    const data = await simGet('/api/simulation/state');
    updateSimulationUI(data);
  } catch (err) {
    console.warn('Failed to fetch simulation state:', err);
  }
}

function connectSimulationWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const wsUrl = `${proto}://${location.host}/api/simulation/ws`;

  try {
    simWs = new WebSocket(wsUrl);

    simWs.onopen = () => {
      console.log('[WS] Simulation Kanban live stream connected');
    };

    simWs.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data === 'pong') return;
        if (data && (data.agents || data.tasks)) {
          updateSimulationUI(data);
        }
      } catch (err) {
        console.warn('Simulation WS parse error:', err);
      }
    };

    simWs.onclose = () => {
      setTimeout(connectSimulationWS, 3000);
    };

    // Heartbeat
    setInterval(() => {
      if (simWs && simWs.readyState === WebSocket.OPEN) {
        simWs.send('ping');
      }
    }, 20000);
  } catch (err) {
    console.warn('WS Init Error:', err);
  }
}

// ─── Master UI Updater ─────────────────────────────────────────
function updateSimulationUI(state) {
  currentSimState = state;

  const pendingConfirmCount = state.pending_confirmations ? state.pending_confirmations.length : 0;
  const pendingHireCount = state.pending_hires ? state.pending_hires.length : 0;
  const totalPending = pendingConfirmCount + pendingHireCount;
  const activeCount = state.active_tasks ? state.active_tasks.length : 0;
  const doneCount = state.confirmed_tasks ? state.confirmed_tasks.length : 0;

  // 1. Update Navigation Badges
  const navBadge = document.getElementById('badge-kanban-pending');
  if (navBadge) {
    if (totalPending > 0) {
      navBadge.style.display = '';
      navBadge.textContent = totalPending;
    } else {
      navBadge.style.display = 'none';
    }
  }

  // 2. Update Top Stat Pills
  const countActiveEl = document.getElementById('kb-count-active');
  const countPendingEl = document.getElementById('kb-count-pending');
  const countDoneEl = document.getElementById('kb-count-done');
  const tgBadgeEl = document.getElementById('topbar-tg-badge');
  const heroTgCount = document.getElementById('kb-tg-count');

  if (countActiveEl) countActiveEl.textContent = activeCount;
  if (countPendingEl) countPendingEl.textContent = totalPending;
  if (countDoneEl) countDoneEl.textContent = doneCount;

  const notifCount = state.notifications ? state.notifications.length : 0;
  if (tgBadgeEl) tgBadgeEl.textContent = notifCount;
  if (heroTgCount) heroTgCount.textContent = notifCount;

  // 3. Render AI Workforce Presence Strip
  renderWorkforceStrip(state.agents || []);

  // 3.1 Render Department Command Hub (1-Click Dispatch)
  renderDeptCommandHub(state.agents || []);

  // 4. Render 4 Kanban Columns
  renderKanbanColumns(state);

  // 5. Render Telegram Live Drawer
  renderTelegramDrawer(state.notifications || []);

  // 6. Real-time sync for active employee workstation if open
  if (document.getElementById('page-workstations')?.classList.contains('active')) {
    if (typeof loadActiveEmployeeDetails === 'function' && typeof _activeEmpId !== 'undefined') {
      loadActiveEmployeeDetails(_activeEmpId);
    }
  }
}

// ─── 1. Render AI Workforce Strip ──────────────────────────────
function renderWorkforceStrip(agents) {
  const container = document.getElementById('workforce-strip-agents');
  if (!container) return;

  if (agents.length === 0) {
    container.innerHTML = `<span style="font-size:0.75rem; color:var(--text-dim);">กำลังโหลดพนักงาน AI...</span>`;
    return;
  }

  container.innerHTML = agents.map(ag => {
    let dotClass = 'idle';
    let statusText = 'พร้อมปฏิบัติงาน';

    if (ag.status === 'awaiting_confirmation') {
      dotClass = 'pending';
      statusText = '🚨 รอยืนยันปิดงาน';
    } else if (ag.status === 'requesting_hire') {
      dotClass = 'hiring';
      statusText = '👥 ขอสร้าง AI เพิ่ม';
    } else if (['coding', 'writing_content', 'reviewing', 'planning', 'active'].includes(ag.status)) {
      dotClass = 'active';
      statusText = ag.status === 'coding' ? '💻 กำลังเขียนโค้ด' :
                   ag.status === 'writing_content' ? '✍️ กำลังเขียนคอนเทนต์' :
                   ag.status === 'reviewing' ? '🔍 กำลังรัน QA' : '⚡ กำลังทำงาน';
    }

    return `
      <div class="agent-presence-chip" onclick="openEmployeeWorkstation('${escapeHtml(ag.department_id || ag.id)}')">
        <div class="agent-avatar-mini">
          ${ag.avatar || '🤖'}
          <span class="agent-status-dot-mini ${dotClass}"></span>
        </div>
        <div>
          <strong style="color:var(--text-primary); font-size:0.78rem;">${escapeHtml(ag.name)}</strong>
          <span style="color:var(--text-dim); font-size:0.7rem; margin-left:2px;">(${statusText})</span>
        </div>
      </div>
    `;
  }).join('');
}

// ─── 2. Render 4 Kanban Columns ───────────────────────────────
function renderKanbanColumns(state) {
  // Update Column Header Badges
  const colCountTodo = document.getElementById('col-count-todo');
  const colCountActive = document.getElementById('col-count-active');
  const colCountPending = document.getElementById('col-count-pending');
  const colCountDone = document.getElementById('col-count-done');

  const pendingConfirmCount = state.pending_confirmations ? state.pending_confirmations.length : 0;
  const pendingHireCount = state.pending_hires ? state.pending_hires.length : 0;
  const totalPending = pendingConfirmCount + pendingHireCount;

  if (colCountTodo) colCountTodo.textContent = '5';
  if (colCountActive) colCountActive.textContent = state.active_tasks ? state.active_tasks.length : 0;
  if (colCountPending) colCountPending.textContent = totalPending;
  if (colCountDone) colCountDone.textContent = state.confirmed_tasks ? state.confirmed_tasks.length : 0;

  // Render Column 1: To Do / Ready-to-Run Presets
  renderColTodo();

  // Render Column 2: In Progress (Live Thought & Progress)
  renderColActive(state.active_tasks || []);

  // Render Column 3: 🚨 Pending Owner Confirmation (HITL)
  renderColPending(state.pending_confirmations || [], state.pending_hires || []);

  // Render Column 4: ✅ Completed & Delivered
  renderColDone(state.confirmed_tasks || []);
}

function renderColTodo() {
  const el = document.getElementById('kanban-col-todo-body');
  if (!el) return;

  el.innerHTML = `
    <!-- Preset 1: Systems Dev -->
    <div class="kanban-card" style="border-left: 3px solid #818cf8;">
      <div class="card-top-row">
        <div class="card-title-text">💻 1. พัฒนาระบบ API & Backend</div>
        <span class="card-category-tag">Systems Dev</span>
      </div>
      <div class="card-assignee-row">
        <span class="card-assignee-avatar">💻</span>
        <div>
          <span class="card-assignee-name">บิ๊นท์ (Lead Dev)</span>
          <span style="color:var(--text-dim); font-size:0.7rem;">+ มุก (QA)</span>
        </div>
      </div>
      <p style="font-size:0.75rem; color:var(--text-muted); line-height:1.35; margin:0;">
        ออกแบบ REST API + JWT Auth + Unit Tests 100% → ส่งให้ Owner ตรวจรับ
      </p>
      <button class="btn-card-inspect" style="background:rgba(129,140,248,0.1); border-color:rgba(129,140,248,0.3); color:#a5b4fc;" onclick="launchSimulationPreset('systems_dev')">
        ⚡ รันงานนี้ทันที
      </button>
    </div>

    <!-- Preset 2: Social Media Content -->
    <div class="kanban-card" style="border-left: 3px solid #f472b6;">
      <div class="card-top-row">
        <div class="card-title-text">📣 2. ผลิต Content Social Media</div>
        <span class="card-category-tag">Marketing</span>
      </div>
      <div class="card-assignee-row">
        <span class="card-assignee-avatar">📣</span>
        <div>
          <span class="card-assignee-name">ลิซ่า (Content Lead)</span>
        </div>
      </div>
      <p style="font-size:0.75rem; color:var(--text-muted); line-height:1.35; margin:0;">
        สคริปต์วิดีโอสั้น TikTok 45 วิ + บทความยาว FB/LinkedIn + AI Visual Prompts
      </p>
      <button class="btn-card-inspect" style="background:rgba(244,114,182,0.1); border-color:rgba(244,114,182,0.3); color:#f472b6;" onclick="launchSimulationPreset('social_content')">
        ⚡ รันงานนี้ทันที
      </button>
    </div>

    <!-- Preset 3: DevOps & Cloud -->
    <div class="kanban-card" style="border-left: 3px solid #fbbf24;">
      <div class="card-top-row">
        <div class="card-title-text">⚡ 3. วางระบบ Cloud & CI/CD</div>
        <span class="card-category-tag">DevOps</span>
      </div>
      <div class="card-assignee-row">
        <span class="card-assignee-avatar">⚡</span>
        <div>
          <span class="card-assignee-name">ก้อง (Cloud DevOps)</span>
        </div>
      </div>
      <p style="font-size:0.75rem; color:var(--text-muted); line-height:1.35; margin:0;">
        จัดทำ Dockerfile, Compose, CI/CD Actions และตรวจสอบความปลอดภัย
      </p>
      <button class="btn-card-inspect" style="background:rgba(251,191,36,0.1); border-color:rgba(251,191,36,0.3); color:#fbbf24;" onclick="launchSimulationPreset('devops')">
        ⚡ รันงานนี้ทันที
      </button>
    </div>

    <!-- Preset 4: QA & Data Analytics -->
    <div class="kanban-card" style="border-left: 3px solid #34d399;">
      <div class="card-top-row">
        <div class="card-title-text">📊 4. ตรวจ QA & วิเคราะห์ Funnel</div>
        <span class="card-category-tag">Analytics</span>
      </div>
      <div class="card-assignee-row">
        <span class="card-assignee-avatar">📊</span>
        <div>
          <span class="card-assignee-name">มุก (QA & Data)</span>
        </div>
      </div>
      <p style="font-size:0.75rem; color:var(--text-muted); line-height:1.35; margin:0;">
        สแกน Conversion Funnel 12,500 รายการ ชี้จุดหลุด OTP Drop-off
      </p>
      <button class="btn-card-inspect" style="background:rgba(52,211,153,0.1); border-color:rgba(52,211,153,0.3); color:#34d399;" onclick="launchSimulationPreset('data_analyst')">
        ⚡ รันงานนี้ทันที
      </button>
    </div>

    <!-- Preset 5: Finance & Cost Controller -->
    <div class="kanban-card" style="border-left: 3px solid #a78bfa;">
      <div class="card-top-row">
        <div class="card-title-text">💰 5. สรุปงบประมาณ & ค่า Token</div>
        <span class="card-category-tag">Finance</span>
      </div>
      <div class="card-assignee-row">
        <span class="card-assignee-avatar">💰</span>
        <div>
          <span class="card-assignee-name">พลอย (Finance)</span>
        </div>
      </div>
      <p style="font-size:0.75rem; color:var(--text-muted); line-height:1.35; margin:0;">
        ตรวจสอบสถิติค่า Token API รายเดือน และคำนวณจุดคุ้มทุน ROI
      </p>
      <button class="btn-card-inspect" style="background:rgba(167,139,250,0.1); border-color:rgba(167,139,250,0.3); color:#a78bfa;" onclick="launchSimulationPreset('accounting')">
        ⚡ รันงานนี้ทันที
      </button>
    </div>

    <!-- Preset 6: Full Launch -->
    <div class="kanban-card" style="border-left: 3px solid #8b5cf6;">
      <div class="card-top-row">
        <div class="card-title-text">🌐 6. Full Launch (Dev + Social)</div>
        <span class="card-category-tag">Full Launch</span>
      </div>
      <div class="card-assignee-row">
        <span class="card-assignee-avatar">🚀</span>
        <div>
          <span class="card-assignee-name">บิ๊นท์ & ลิซ่า</span>
        </div>
      </div>
      <p style="font-size:0.75rem; color:var(--text-muted); line-height:1.35; margin:0;">
        บิ๊นท์พัฒนา Microservice และลิซ่าทำแคมเปญโปรโมตเปิดตัวคู่กัน
      </p>
      <button class="btn-card-inspect" style="background:rgba(139,92,246,0.1); border-color:rgba(139,92,246,0.3); color:#c4b5fd;" onclick="launchSimulationPreset('collaborative')">
        ⚡ รันงานนี้ทันที
      </button>
    </div>

    <!-- Preset 7: AI Hiring -->
    <div class="kanban-card" style="border-left: 3px solid #a855f7;">
      <div class="card-top-row">
        <div class="card-title-text">👥 7. AI ขอเสนอจ้างทีมเพิ่ม</div>
        <span class="card-category-tag">HR Scaling</span>
      </div>
      <div class="card-assignee-row">
        <span class="card-assignee-avatar">🗂️</span>
        <div>
          <span class="card-assignee-name">อิงฟ้า (เลขา AI)</span>
        </div>
      </div>
      <p style="font-size:0.75rem; color:var(--text-muted); line-height:1.35; margin:0;">
        อิงฟ้ายื่นขอจัดจ้างพนักงาน AI ผู้เชี่ยวชาญเฉพาะทางเข้าทีม รอ Owner อนุมัติ
      </p>
      <button class="btn-card-inspect" style="background:rgba(168,85,247,0.1); border-color:rgba(168,85,247,0.3); color:#d8b4fe;" onclick="launchSimulationPreset('hiring_request')">
        ⚡ รันงานนี้ทันที
      </button>
    </div>
  `;
}

// ─── Render Department Command Hub ────────────────────────────
function renderDeptCommandHub(agents = []) {
  const container = document.getElementById('dept-cmd-grid');
  if (!container) return;

  const agentStatusMap = {};
  agents.forEach(a => {
    agentStatusMap[a.department_id || a.id] = a;
  });

  const depts = Object.values(ENTERPRISE_DEPARTMENTS);

  container.innerHTML = depts.map(dept => {
    const agState = agentStatusMap[dept.id];
    const isBusy = agState && ['coding', 'writing_content', 'reviewing', 'planning', 'active'].includes(agState.status);
    const isPending = agState && agState.status === 'awaiting_confirmation';

    let statusBadge = `<span class="dept-status-pill">🟢 พร้อมรับงาน</span>`;
    if (isPending) {
      statusBadge = `<span class="dept-status-pill" style="background:rgba(245,158,11,0.15); border-color:rgba(245,158,11,0.4); color:#fbbf24;">🚨 รออนุมัติงาน</span>`;
    } else if (isBusy) {
      statusBadge = `<span class="dept-status-pill" style="background:rgba(99,102,241,0.15); border-color:rgba(99,102,241,0.4); color:#a5b4fc;">⚡ กำลังทำ</span>`;
    }

    return `
      <div class="dept-cmd-card" style="--card-accent:${dept.color}; --card-glow:${dept.glow};" id="card-${dept.id}">
        <div>
          <div class="dept-card-top">
            <div class="dept-avatar-wrap">${dept.avatar}</div>
            <div class="dept-meta-wrap">
              <div class="dept-name-text" title="${escapeHtml(dept.name)}">${escapeHtml(dept.name)}</div>
              <div class="dept-pm-text">
                <span>${escapeHtml(dept.pm)}</span>
                ${statusBadge}
              </div>
            </div>
          </div>
          <div class="dept-skills-desc" title="${escapeHtml(dept.skills)}">
            🎯 ${escapeHtml(dept.skills)}
          </div>
        </div>

        <div>
          <button class="dept-quick-preset-btn" onclick="quickDispatchDept('${dept.id}', '${escapeHtml(dept.quickPrompt)}')" title="คลิกเพื่อสั่งงานตาม Preset ทันที">
            <span>⚡ ${escapeHtml(dept.quickAction)}</span>
            <span style="opacity:0.6; font-size:0.65rem;">1-Click</span>
          </button>
          <button class="btn-dept-dispatch" style="--btn-border:${dept.btnBorder}; --btn-bg:${dept.btnBg}; --btn-hover-bg:${dept.btnHover}; --btn-color:${dept.btnColor};" onclick="openDeptDispatchModal('${dept.id}')">
            <span>🚀 สั่งงานแผนกนี้</span>
            <span style="font-size:0.85rem;">→</span>
          </button>
          <button class="btn-card-inspect" style="margin-top:6px; width:100%; font-size:0.75rem; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); color:var(--text-muted); border-radius:var(--radius-sm); padding:5px 8px;" onclick="openEmployeeWorkstation('${dept.id}')">
            <span>👤 ดูโต๊ะทำงาน & ประวัติงาน</span>
          </button>
        </div>
      </div>
    `;
  }).join('');
}

// ─── Department Dispatch Modal Logic ──────────────────────────
function openDeptDispatchModal(deptId) {
  const dept = ENTERPRISE_DEPARTMENTS[deptId];
  if (!dept) {
    simToast(`ไม่พบข้อมูลแผนก ${deptId}`, 'warning');
    return;
  }

  const avatarEl = document.getElementById('dispatch-modal-avatar');
  const titleEl = document.getElementById('dispatch-modal-title');
  const subEl = document.getElementById('dispatch-modal-subtitle');
  const skillsEl = document.getElementById('dispatch-modal-skills');
  const deptIdEl = document.getElementById('dispatch-modal-dept-id');
  const presetEl = document.getElementById('dispatch-modal-preset');
  const templatesContainer = document.getElementById('dispatch-templates-container');
  const promptInput = document.getElementById('dispatch-prompt-input');

  if (avatarEl) avatarEl.textContent = dept.avatar;
  if (titleEl) titleEl.textContent = `สั่งงานตรง — ${dept.name}`;
  if (subEl) subEl.textContent = `ผู้รับผิดชอบหลัก: ${dept.pm} (${dept.role})`;
  if (skillsEl) skillsEl.textContent = dept.skills;
  if (deptIdEl) deptIdEl.value = dept.id;
  if (presetEl) presetEl.value = dept.preset;

  if (templatesContainer) {
    templatesContainer.innerHTML = dept.templates.map(tpl => `
      <div class="dispatch-template-chip" onclick="selectDispatchTemplate('${escapeHtml(tpl).replace(/'/g, "\\'")}')">
        <span>💡</span>
        <span style="flex:1;">${escapeHtml(tpl)}</span>
        <span style="font-size:0.7rem; color:var(--brand-400);">เลือก ↵</span>
      </div>
    `).join('');
  }

  if (promptInput) {
    promptInput.value = dept.templates[0] || '';
  }

  if (typeof openModal === 'function') {
    openModal('modal-dept-dispatch');
  } else {
    const m = document.getElementById('modal-dept-dispatch');
    if (m) m.classList.add('active');
  }
}

function selectDispatchTemplate(templateText) {
  const promptInput = document.getElementById('dispatch-prompt-input');
  if (promptInput) {
    promptInput.value = templateText;
    promptInput.focus();
    simToast('เลือกคำสั่งงานแล้ว — สามารถปรับแต่งข้อความเพิ่มเติมได้เลย', 'info');
  }
}

async function submitDeptDispatch() {
  const deptIdEl = document.getElementById('dispatch-modal-dept-id');
  const presetEl = document.getElementById('dispatch-modal-preset');
  const promptInput = document.getElementById('dispatch-prompt-input');

  const deptId = deptIdEl ? deptIdEl.value : '';
  const preset = presetEl ? presetEl.value : 'systems_dev';
  const promptText = promptInput ? promptInput.value.trim() : '';

  if (!promptText) {
    simToast('กรุณาระบุรายละเอียดคำสั่งงานที่ต้องการให้ AI ปฏิบัติงาน', 'warning');
    return;
  }

  const dept = ENTERPRISE_DEPARTMENTS[deptId] || { name: 'ทีม AI', pm: 'AI' };
  const btn = document.getElementById('btn-dispatch-submit');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>⏳ กำลังส่งมอบงานให้ ${escapeHtml(dept.pm)}...</span>`;
  }

  try {
    const res = await simPost('/api/simulation/start', {
      preset: preset,
      prompt: promptText
    });

    if (typeof closeModal === 'function') {
      closeModal('modal-dept-dispatch');
    } else {
      const m = document.getElementById('modal-dept-dispatch');
      if (m) m.classList.remove('active');
    }

    simToast(`🚀 มอบหมายงานให้ ${dept.pm} เรียบร้อย — AI เริ่มกระบวนการทำงานทันที`, 'success');
    fetchSimulationState();

    // เลื่อนหน้าจอลงไปยังบอร์ด Kanban เพื่อให้เห็นการทำงานสด
    const kb = document.querySelector('.kanban-board');
    if (kb) {
      kb.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  } catch (err) {
    simToast(`เกิดข้อผิดพลาด: ${err.message}`, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<span>⚡ ส่งคำสั่งและเริ่มงานทันที (Autonomous Execution)</span>`;
    }
  }
}

async function quickDispatchDept(deptId, promptText) {
  const dept = ENTERPRISE_DEPARTMENTS[deptId];
  if (!dept) return;

  try {
    simToast(`🚀 กำลังส่งมอบงานให้ ${dept.pm} เริ่มดำเนินการ...`, 'info');
    await simPost('/api/simulation/start', {
      preset: dept.preset,
      prompt: promptText
    });
    simToast(`ส่งงาน "${promptText.slice(0, 35)}..." ให้ ${dept.pm} เรียบร้อย!`, 'success');
    fetchSimulationState();

    const kb = document.querySelector('.kanban-board');
    if (kb) {
      kb.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  } catch (err) {
    simToast(`เกิดข้อผิดพลาด: ${err.message}`, 'error');
  }
}

function renderColActive(activeTasks) {
  const el = document.getElementById('kanban-col-active-body');
  if (!el) return;

  if (activeTasks.length === 0) {
    el.innerHTML = `
      <div class="kanban-empty-state">
        <div class="empty-icon">☕</div>
        <strong style="color:var(--text-muted);">ทีม AI พร้อมปฏิบัติงาน</strong>
        <span>เลือก Preset ทางซ้าย หรือพิมพ์สั่งงานที่ช่องด้านบนได้เลย</span>
      </div>
    `;
    return;
  }

  el.innerHTML = activeTasks.map(task => {
    // Find assigned agent
    const agent = (currentSimState.agents || []).find(a => a.id === task.assigned_agent_id) || {};
    const progress = agent.progress || 45;
    const actionText = agent.current_action || 'กำลังดำเนินการ...';
    const thoughtText = agent.current_thought || '';

    return `
      <div class="kanban-card" style="border-left: 3px solid #10b981;">
        <div class="card-top-row">
          <div class="card-title-text">${escapeHtml(task.title)}</div>
          <span class="card-category-tag" style="background:rgba(16,185,129,0.15); color:#34d399;">
            ● กำลังรัน
          </span>
        </div>

        <div class="card-assignee-row" style="cursor:pointer;" onclick="openEmployeeWorkstation('${escapeHtml(task.assigned_agent_id || task.department_id)}')" title="คลิกเพื่อดูโต๊ะทำงานพนักงานคนนี้">
          <span class="card-assignee-avatar">${agent.avatar || '🤖'}</span>
          <div>
            <span class="card-assignee-name">${escapeHtml(task.assigned_agent_name)}</span>
            <div style="font-size:0.7rem; color:var(--text-dim);">${escapeHtml(task.department_id)} ➔ ดูโต๊ะทำงาน</div>
          </div>
        </div>

        <div class="card-progress-box">
          <div class="card-action-text">
            <span>⚡</span>
            <span>${escapeHtml(actionText)}</span>
          </div>

          ${thoughtText ? `
            <div class="card-thought-bubble">
              💭 "${escapeHtml(thoughtText)}"
            </div>
          ` : ''}

          <div class="card-progress-bar">
            <div class="card-progress-fill" style="width: ${progress}%"></div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function renderColPending(pendingTasks, pendingHires) {
  const el = document.getElementById('kanban-col-pending-body');
  if (!el) return;

  const total = pendingTasks.length + pendingHires.length;
  if (total === 0) {
    el.innerHTML = `
      <div class="kanban-empty-state">
        <div class="empty-icon">🎉</div>
        <strong style="color:var(--text-muted);">ไม่มีงานค้างรอการตัดสินใจ</strong>
        <span>เมื่องานเสร็จสมบูรณ์ จะถูกส่งมาที่กล่องนี้เพื่อให้คุณยืนยันก่อนปิดงาน</span>
      </div>
    `;
    return;
  }

  let html = '';

  // 1. Render Deliverables awaiting Owner Confirmation
  pendingTasks.forEach(task => {
    const deliverable = task.deliverable || {};
    const hasFiles = deliverable.files_created && deliverable.files_created.length > 0;
    const hasSocial = deliverable.social_posts && deliverable.social_posts.length > 0;

    html += `
      <div class="kanban-card pending-confirm-card" id="task-card-${task.id}">
        <div class="card-top-row">
          <div class="card-title-text" style="color:#fbbf24;">
            🚨 ${escapeHtml(task.title)}
          </div>
        </div>

        <div class="card-assignee-row" style="cursor:pointer;" onclick="openEmployeeWorkstation('${escapeHtml(task.assigned_agent_id || task.department_id)}')" title="คลิกเพื่อดูโต๊ะทำงานพนักงานคนนี้">
          <span class="card-assignee-avatar">👤</span>
          <div>
            <span class="card-assignee-name">${escapeHtml(task.assigned_agent_name)}</span>
            <span style="font-size:0.7rem; color:var(--text-dim);">| ส่งเมื่อ: ${formatIsoTime(task.submitted_at)} ➔ ดูโต๊ะทำงาน</span>
          </div>
        </div>

        <div class="card-deliverable-summary">
          <strong>สรุปผลงาน:</strong> ${escapeHtml(deliverable.summary || task.prompt)}
        </div>

        <div style="display:flex; gap:0.35rem; flex-wrap:wrap; font-size:0.7rem;">
          ${hasFiles ? `<span class="card-category-tag" style="background:rgba(90,110,240,0.15); color:#818cf8;">📄 Code พร้อมส่ง</span>` : ''}
          ${hasSocial ? `<span class="card-category-tag" style="background:rgba(244,114,182,0.15); color:#f472b6;">📱 Social Content</span>` : ''}
          <span class="card-category-tag" style="background:rgba(16,185,129,0.15); color:#34d399;">✓ QA 100% Passed</span>
        </div>

        <div class="card-actions-row">
          <button class="btn-card-inspect" onclick="openDeliverableModal('${task.id}')">
            🔍 ตรวจดูผลงาน
          </button>
          <button class="btn-card-approve" onclick="confirmTaskAction('${task.id}')">
            ✅ อนุมัติปิดงาน
          </button>
          <button class="btn-card-revise" title="ขอให้ AI ปรับปรุงแก้ไข" onclick="openRevisionDialog('${task.id}')">
            🔄 แก้ไข
          </button>
        </div>
      </div>
    `;
  });

  // 2. Render Hiring Proposals
  pendingHires.forEach(prop => {
    html += `
      <div class="kanban-card hiring-proposal-card" id="prop-card-${prop.id}">
        <div class="card-top-row">
          <div class="card-title-text" style="color:#d8b4fe;">
            👥 ขอจัดจ้าง: <strong>${escapeHtml(prop.proposed_role)}</strong>
          </div>
          <span class="badge-hiring-request">AI เสนอทีม</span>
        </div>

        <div class="card-assignee-row" style="cursor:pointer;" onclick="openEmployeeWorkstation('${escapeHtml(prop.department_id || prop.requested_by_agent_id)}')" title="คลิกเพื่อดูโต๊ะทำงานพนักงานคนนี้">
          <span class="card-assignee-avatar">${prop.avatar || '⚡'}</span>
          <div>
            <span class="card-assignee-name">${escapeHtml(prop.requested_by_name)} ยื่นเรื่อง</span>
            <div style="font-size:0.7rem; color:var(--text-dim);">${escapeHtml(prop.department_name)} ➔ ดูโต๊ะทำงาน</div>
          </div>
        </div>

        <div style="font-size:0.76rem; color:#cbd5e1; background:rgba(0,0,0,0.25); padding:0.5rem 0.65rem; border-radius:6px; border-left:2px solid #a855f7;">
          <strong>เหตุผลความจำเป็น:</strong> ${escapeHtml(prop.reason_and_need)}
        </div>

        <div class="card-actions-row">
          <button class="btn-card-revise" onclick="rejectHiringAction('${prop.id}')">
            ❌ ปฏิเสธ
          </button>
          <button class="btn-card-approve" style="background:linear-gradient(135deg, #8b5cf6, #7c3aed);" onclick="approveHiringAction('${prop.id}')">
            ✨ อนุมัติรับเข้าทีมทันที
          </button>
        </div>
      </div>
    `;
  });

  el.innerHTML = html;
}

function renderColDone(confirmedTasks) {
  const el = document.getElementById('kanban-col-done-body');
  if (!el) return;

  if (confirmedTasks.length === 0) {
    el.innerHTML = `
      <div class="kanban-empty-state">
        <div class="empty-icon">📁</div>
        <strong style="color:var(--text-muted);">ยังไม่มีงานที่ปิดสมบูรณ์</strong>
      </div>
    `;
    return;
  }

  el.innerHTML = confirmedTasks.map(task => {
    return `
      <div class="kanban-card completed-card" style="border-left: 3px solid #14b8a6;">
        <div class="card-top-row">
          <div class="card-title-text">${escapeHtml(task.title)}</div>
          <span class="badge-confirmed-ok">✓ อนุมัติแล้ว</span>
        </div>

        <div class="card-assignee-row" style="cursor:pointer;" onclick="openEmployeeWorkstation('${escapeHtml(task.assigned_agent_id || task.department_id)}')" title="คลิกเพื่อดูโต๊ะทำงานพนักงานคนนี้">
          <span class="card-assignee-avatar">✅</span>
          <div>
            <span class="card-assignee-name">${escapeHtml(task.assigned_agent_name)}</span>
            <span style="font-size:0.7rem; color:var(--text-dim);">| ปิดงาน: ${formatIsoTime(task.confirmed_at || task.submitted_at)} ➔ ดูโต๊ะทำงาน</span>
          </div>
        </div>

        <p style="font-size:0.74rem; color:var(--text-muted); line-height:1.35; margin:0;">
          ${escapeHtml(task.deliverable?.summary || task.prompt)}
        </p>

        <div style="display:flex; align-items:center; justify-content:space-between; margin-top:0.25rem;">
          <span style="font-size:0.7rem; color:#2dd4bf;">📖 บันทึกสู่ Memory แล้ว</span>
          <button class="btn-card-inspect" style="padding:0.25rem 0.6rem; font-size:0.72rem;" onclick="openDeliverableModal('${task.id}')">
            📄 ดูผลงาน
          </button>
        </div>
      </div>
    `;
  }).join('');
}

// ─── 3. Rich Deliverable Detail Modal ─────────────────────────
function openDeliverableModal(taskId) {
  const allTasks = [
    ...(currentSimState.pending_confirmations || []),
    ...(currentSimState.active_tasks || []),
    ...(currentSimState.confirmed_tasks || []),
    ...(currentSimState.tasks || [])
  ];

  const task = allTasks.find(t => t.id === taskId);
  if (!task) {
    simToast('ไม่พบข้อมูลผลงาน Task นี้', 'warning');
    return;
  }

  activeDeliverableTaskId = taskId;
  const deliverable = task.deliverable || {};
  const isPending = task.status === 'AWAITING_CONFIRMATION';

  // Modal Title & Metadata
  document.getElementById('modal-del-title').textContent = task.title;
  document.getElementById('modal-del-meta').textContent = `ผู้ส่งมอบ: ${task.assigned_agent_name} | แผนก: ${task.department_id} | สถานะ: ${task.status}`;

  // Pane 1: Summary & QA
  document.getElementById('modal-del-summary').textContent = deliverable.summary || task.prompt || 'ไม่มีสรุปเพิ่มเติม';
  document.getElementById('modal-del-qa').textContent = deliverable.qa_report || '✅ ผ่านเกณฑ์มาตรฐานการตรวจสอบคุณภาพ';
  document.getElementById('modal-del-details').textContent = deliverable.details || '—';

  // Pane 2: Code Files
  const codePane = document.getElementById('modal-del-code-container');
  if (deliverable.files_created && deliverable.files_created.length > 0) {
    codePane.innerHTML = deliverable.files_created.map(f => `
      <div style="margin-bottom:1rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
          <span style="font-size:0.8rem; font-weight:600; color:var(--brand-400);">📄 ${escapeHtml(f.name)} (${f.language})</span>
          <button class="btn btn-sm" onclick="copyToClipboard('${escapeHtml(f.content).replace(/'/g, "\\'")}')">📋 คัดลอกโค้ด</button>
        </div>
        <pre class="code-preview-block"><code>${escapeHtml(f.content)}</code></pre>
      </div>
    `).join('');
  } else {
    codePane.innerHTML = `<div style="text-align:center; padding:2rem; opacity:0.5;">ไม่มีไฟล์ซอร์สโค้ดในงานชิ้นนี้</div>`;
  }

  // Pane 3: Social Media Posts
  const socialPane = document.getElementById('modal-del-social-container');
  if (deliverable.social_posts && deliverable.social_posts.length > 0) {
    socialPane.innerHTML = deliverable.social_posts.map(post => `
      <div class="social-post-preview-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.6rem;">
          <strong style="color:#f472b6; font-size:0.88rem;">📱 ${escapeHtml(post.platform)}</strong>
          <span style="font-size:0.75rem; color:var(--text-dim);">${escapeHtml(post.hashtags || '')}</span>
        </div>
        <div style="background:rgba(244,114,182,0.1); border-left:3px solid #ec4899; padding:0.5rem 0.75rem; border-radius:4px; font-weight:600; font-size:0.84rem; color:#fbcfe8; margin-bottom:0.6rem;">
          🪝 Hook: "${escapeHtml(post.hook)}"
        </div>
        <pre class="code-preview-block" style="color:#f1f5f9; background:#12151d; font-family:var(--font-body);">${escapeHtml(post.content)}</pre>
        ${post.image_prompt ? `
          <div style="margin-top:0.6rem; font-size:0.78rem; color:#c4b5fd; background:rgba(139,92,246,0.1); padding:0.5rem 0.75rem; border-radius:4px; border-left:2px solid #8b5cf6;">
            🎨 <b>AI Image Prompt:</b> ${escapeHtml(post.image_prompt)}
          </div>
        ` : ''}
      </div>
    `).join('');
  } else {
    socialPane.innerHTML = `<div style="text-align:center; padding:2rem; opacity:0.5;">ไม่มีคอนเทนต์ Social Media ในงานชิ้นนี้</div>`;
  }

  // Pane 4: Checklist
  const checkPane = document.getElementById('modal-del-checklist');
  if (deliverable.checklist && deliverable.checklist.length > 0) {
    checkPane.innerHTML = `
      <ul style="padding-left:1.5rem; line-height:1.7; font-size:0.88rem;">
        ${deliverable.checklist.map(item => `<li>${escapeHtml(item)}</li>`).join('')}
      </ul>
    `;
  } else {
    checkPane.innerHTML = `<div style="opacity:0.5;">ไม่มี Checklist เพิ่มเติม</div>`;
  }

  // Footer Actions
  const footerActions = document.getElementById('modal-del-footer-actions');
  if (isPending) {
    footerActions.innerHTML = `
      <button class="btn" onclick="openRevisionDialog('${task.id}'); closeModal('modal-deliverable-detail');">
        🔄 ขอแก้ไขงาน
      </button>
      <button class="btn btn-primary" style="background:linear-gradient(135deg, #10b981, #059669);" onclick="confirmTaskAction('${task.id}'); closeModal('modal-deliverable-detail');">
        ✅ ยืนยันอนุมัติปิดงาน (Confirm & Close)
      </button>
    `;
  } else {
    footerActions.innerHTML = `
      <span style="font-size:0.82rem; color:#34d399; margin-right:auto;">✓ งานนี้ได้รับการอนุมัติปิดงานโดย Owner แล้ว</span>
      <button class="btn" onclick="closeModal('modal-deliverable-detail')">ปิดหน้าต่าง</button>
    `;
  }

  // Set default tab
  switchDeliverableTab('summary');

  // Open modal
  const modalEl = document.getElementById('modal-deliverable-detail');
  if (modalEl) modalEl.classList.add('active');
}

function switchDeliverableTab(tabName) {
  document.querySelectorAll('.del-tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tabName));
  document.querySelectorAll('.deliverable-tab-pane').forEach(p => p.classList.toggle('active', p.id === `del-pane-${tabName}`));
}

// ─── 4. Slide-out Telegram Drawer ─────────────────────────────
function toggleTelegramDrawer() {
  const drawer = document.getElementById('telegram-drawer');
  const overlay = document.getElementById('telegram-drawer-overlay');
  if (!drawer) return;

  const isOpen = drawer.classList.contains('open');
  if (isOpen) {
    drawer.classList.remove('open');
    if (overlay) overlay.classList.remove('open');
  } else {
    drawer.classList.add('open');
    if (overlay) overlay.classList.add('open');
  }
}

function renderTelegramDrawer(notifications) {
  const container = document.getElementById('telegram-drawer-list');
  if (!container) return;

  if (notifications.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding:3rem 1rem; color:var(--text-dim); font-size:0.85rem;">
        <div style="font-size:2rem; margin-bottom:0.5rem;">📭</div>
        ยังไม่มีประวัติการแจ้งเตือน Telegram
      </div>
    `;
    return;
  }

  container.innerHTML = notifications.map(n => {
    let badgeClass = 'confirm';
    let badgeLabel = 'Alert';

    if (n.type === 'confirmation_request') {
      badgeClass = 'confirm';
      badgeLabel = '🚨 รอยืนยันปิดงาน';
    } else if (n.type === 'hiring_request') {
      badgeClass = 'hiring';
      badgeLabel = '👥 ขอจัดจ้าง AI';
    } else if (n.type === 'task_confirmed') {
      badgeClass = 'confirmed';
      badgeLabel = '✅ อนุมัติแล้ว';
    }

    return `
      <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); border-radius:8px; padding:0.85rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.35rem;">
          <span style="font-size:0.7rem; font-weight:700; color:#fbbf24;">${badgeLabel}</span>
          <span style="font-size:0.7rem; color:var(--text-dim);">${escapeHtml(n.timestamp)}</span>
        </div>
        <strong style="font-size:0.82rem; color:var(--text-primary); display:block; margin-bottom:0.3rem;">
          ${escapeHtml(n.title)}
        </strong>
        <div style="font-size:0.76rem; color:var(--text-muted); line-height:1.4;">
          ${escapeHtml(n.message.replace(/<[^>]+>/g, ' ')).slice(0, 160)}...
        </div>
      </div>
    `;
  }).join('');
}

// ─── Actions & Confirmation Handlers ───────────────────────────
async function confirmTaskAction(taskId) {
  try {
    const res = await simPost(`/api/simulation/tasks/${taskId}/confirm`, {
      owner_name: 'Owner',
      feedback: 'ยืนยันอนุมัติปิดงานเรียบร้อยโดย Owner — ผลงานสมบูรณ์แบบ 100%'
    });
    simToast('✅ อนุมัติปิดงานสำเร็จ! บันทึกลง Memory และแจ้งเตือน Telegram เรียบร้อย', 'success');
    fetchSimulationState();
  } catch (err) {
    simToast(`เกิดข้อผิดพลาด: ${err.message}`, 'error');
  }
}

function openRevisionDialog(taskId) {
  const feedback = prompt('กรุณาระบุสิ่งที่ต้องการให้ AI ปรับปรุงแก้ไข (เช่น เพิ่ม Error Handling, ปรับ Hook ให้น่าสนใจขึ้น):');
  if (feedback && feedback.trim()) {
    submitRevision(taskId, feedback.trim());
  }
}

async function submitRevision(taskId, feedback) {
  try {
    await simPost(`/api/simulation/tasks/${taskId}/revise`, {
      feedback: feedback,
      owner_name: 'Owner'
    });
    simToast('🔄 ส่งคำขอแก้ไขไปยังทีม AI เรียบร้อย — AI กำลังเร่งปรับปรุงงานทันที', 'warning');
    fetchSimulationState();
  } catch (err) {
    simToast(`เกิดข้อผิดพลาด: ${err.message}`, 'error');
  }
}

async function approveHiringAction(proposalId) {
  try {
    const res = await simPost(`/api/simulation/hire/${proposalId}/approve`, {
      owner_name: 'Owner'
    });
    simToast('✨ อนุมัติจัดจ้าง AI สำเร็จ! บรรจุพนักงานใหม่เข้าทีมเรียบร้อย', 'success');
    fetchSimulationState();
  } catch (err) {
    simToast(`เกิดข้อผิดพลาด: ${err.message}`, 'error');
  }
}

async function rejectHiringAction(proposalId) {
  const reason = prompt('ระบุเหตุผลที่ปฏิเสธคำขอสร้าง AI (ถ้ามี):') || 'ยังไม่มีความจำเป็นในขณะนี้';
  try {
    await simPost(`/api/simulation/hire/${proposalId}/reject`, {
      reason: reason
    });
    simToast('ปฏิเสธคำขอจัดจ้างเรียบร้อย', 'info');
    fetchSimulationState();
  } catch (err) {
    simToast(`เกิดข้อผิดพลาด: ${err.message}`, 'error');
  }
}

// ─── Launchpad Presets & Custom Command ────────────────────────
async function launchSimulationPreset(presetKey) {
  try {
    simToast('🚀 กำลังเริ่มดำเนินงานตามคำสั่ง...', 'info');
    const res = await simPost('/api/simulation/start', {
      preset: presetKey,
      prompt: ''
    });
    simToast(`เริ่มงาน '${res.detail.title}' เรียบร้อย — ติดตามความคืบหน้าสดในบอร์ด Kanban`, 'success');
    fetchSimulationState();
  } catch (err) {
    simToast(`เกิดข้อผิดพลาด: ${err.message}`, 'error');
  }
}

async function kbLaunchCustom() {
  const input = document.getElementById('kb-command-input');
  if (!input || !input.value.trim()) {
    simToast('กรุณาระบุคำสั่งงานที่ต้องการให้ทีม AI ทำ', 'warning');
    return;
  }
  const text = input.value.trim();
  input.value = '';

  try {
    simToast(`🚀 ส่งคำสั่ง "${text}" เข้าสู่ทีม AI เรียบร้อย`, 'info');
    await simPost('/api/simulation/start', {
      preset: 'custom',
      prompt: text
    });
    fetchSimulationState();
  } catch (err) {
    simToast(`เกิดข้อผิดพลาด: ${err.message}`, 'error');
  }
}

async function resetSimulationStudio() {
  if (!confirm('ต้องการรีเซ็ตสถานะของทีม AI และ Task ทั้งหมดกลับสู่ค่าเริ่มต้น (Standby) ใช่หรือไม่?')) return;
  try {
    await simPost('/api/simulation/reset', {});
    simToast('รีเซ็ตสถานะทีมงานเรียบร้อย', 'info');
    fetchSimulationState();
  } catch (err) {
    simToast(`เกิดข้อผิดพลาด: ${err.message}`, 'error');
  }
}

function openEmployeeWorkstation(deptId) {
  if (typeof navigateTo === 'function') {
    navigateTo('workstations');
    setTimeout(() => {
      if (typeof switchWorkstationEmployee === 'function') {
        switchWorkstationEmployee(deptId);
      }
    }, 50);
  }
}

function openDirectAgentModal(deptId, agentName, roleTitle) {
  if (typeof openDirectCommandModal === 'function') {
    openDirectCommandModal(deptId, `${agentName} (${roleTitle})`);
  } else {
    const cmd = prompt(`พิมพ์คำสั่งงานตรงไปยัง ${agentName}:`);
    if (cmd && cmd.trim()) {
      simPost('/api/simulation/start', { preset: 'custom', prompt: `[สั่งงานตรง ${agentName}] ${cmd.trim()}` })
        .then(() => {
          simToast(`ส่งคำสั่งไปยัง ${agentName} เรียบร้อย`, 'success');
          fetchSimulationState();
        });
    }
  }
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    simToast('📋 คัดลอกลง Clipboard เรียบร้อย', 'success');
  }).catch(() => {
    simToast('ไม่สามารถคัดลอกได้', 'error');
  });
}

// ─── Helpers ──────────────────────────────────────────────────
function formatIsoTime(isoStr) {
  if (!isoStr) return '--:--';
  try {
    const d = new Date(isoStr);
    return d.toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return isoStr;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Window Bindings
window.initSimulation = initSimulation;
window.fetchSimulationState = fetchSimulationState;
window.confirmTaskAction = confirmTaskAction;
window.openRevisionDialog = openRevisionDialog;
window.submitRevision = submitRevision;
window.approveHiringAction = approveHiringAction;
window.rejectHiringAction = rejectHiringAction;
window.launchSimulationPreset = launchSimulationPreset;
window.kbLaunchCustom = kbLaunchCustom;
window.resetSimulationStudio = resetSimulationStudio;
window.openDeliverableModal = openDeliverableModal;
window.switchDeliverableTab = switchDeliverableTab;
window.toggleTelegramDrawer = toggleTelegramDrawer;
window.openDirectAgentModal = openDirectAgentModal;
window.openEmployeeWorkstation = openEmployeeWorkstation;
window.copyToClipboard = copyToClipboard;
window.openDeptDispatchModal = openDeptDispatchModal;
window.selectDispatchTemplate = selectDispatchTemplate;
window.submitDeptDispatch = submitDeptDispatch;
window.quickDispatchDept = quickDispatchDept;
window.renderDeptCommandHub = renderDeptCommandHub;
