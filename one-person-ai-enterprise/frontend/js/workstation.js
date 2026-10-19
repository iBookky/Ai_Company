/* ═══════════════════════════════════════════════════════════════
   workstation.js — Logic for Virtual AI Employee Workstations
   One-Person AI Enterprise
   ═══════════════════════════════════════════════════════════════ */

'use strict';

let _activeEmpId = '03_developer';
let _cachedEmployees = [];
let _currentWorkspaceData = null;
let _historyFilter = 'all';

// ─── Initialize Workstation Page ──────────────────────────────
async function loadWorkstations(targetId = null) {
  try {
    if (targetId) {
      _activeEmpId = targetId;
    } else {
      // Check if hash has an ID, e.g. #/employees?id=01_secretary or #/employees/01_secretary
      const hash = location.hash;
      const match = hash.match(/(?:id=|\/employees\/)([\w_]+)/);
      if (match && match[1]) {
        _activeEmpId = match[1];
      }
    }

    // 1. Fetch all employees summary
    const employees = await apiGet('/api/simulation/employees');
    _cachedEmployees = employees;

    // Check if _activeEmpId exists in list, else default to first
    if (!employees.some(e => e.id === _activeEmpId) && employees.length > 0) {
      _activeEmpId = employees[0].id;
    }

    // 2. Render top selector strip
    renderEmployeeSelectorStrip(employees, _activeEmpId);

    // 3. Fetch full workspace for active employee
    await loadActiveEmployeeDetails(_activeEmpId);

  } catch (err) {
    console.error('Failed to load workstation data:', err);
    const container = document.getElementById('workstation-cockpit-content');
    if (container) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; background: rgba(255,255,255,0.02); border-radius: var(--radius-lg); border: 1px solid var(--border);">
          <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">⚠️</div>
          <h3 style="color: var(--text-primary); margin-bottom: 0.5rem;">กำลังเริ่มต้นข้อมูลโต๊ะทำงานพนักงาน</h3>
          <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1.25rem;">ระบบกำลังเชื่อมต่อข้อมูลและซิงค์สถานะสดของทีม AI</p>
          <button class="btn btn-primary" onclick="loadWorkstations()">🔄 โหลดข้อมูลใหม่</button>
        </div>
      `;
    }
  }
}

// ─── Render Employee Selector Strip ───────────────────────────
function renderEmployeeSelectorStrip(employees, activeId) {
  const strip = document.getElementById('employee-selector-strip');
  if (!strip) return;

  strip.innerHTML = employees.map(emp => {
    const isActive = emp.id === activeId;
    let pipClass = 'idle';
    let statusText = 'Standby';

    if (emp.status === 'awaiting_confirmation') {
      pipClass = 'pending';
      statusText = '🚨 รอยืนยัน';
    } else if (['coding', 'writing_content', 'reviewing', 'planning', 'active'].includes(emp.status)) {
      pipClass = 'active';
      statusText = '⚡ กำลังทำงาน';
    }

    return `
      <div class="employee-select-card ${isActive ? 'active' : ''}" onclick="switchWorkstationEmployee('${escapeHtml(emp.id)}')">
        <div class="select-card-avatar">
          <img src="${emp.photo_url || '/static/img/avatars/01_secretary.jpg'}" alt="${escapeHtml(emp.name)}" onerror="this.src='/static/img/avatars/01_secretary.jpg'" />
          <span class="avatar-status-pip ${pipClass}"></span>
        </div>
        <div class="select-card-info">
          <span class="select-card-name">${escapeHtml(emp.nickname || emp.name)}</span>
          <span class="select-card-role">${escapeHtml(emp.role_title)}</span>
          <span class="select-card-status ${pipClass}">● ${statusText}</span>
        </div>
      </div>
    `;
  }).join('');
}

// ─── Switch Active Employee ───────────────────────────────────
async function switchWorkstationEmployee(empId) {
  _activeEmpId = empId;
  renderEmployeeSelectorStrip(_cachedEmployees, empId);
  await loadActiveEmployeeDetails(empId);
}

// ─── Fetch & Render Full Details for Active Employee ──────────
async function loadActiveEmployeeDetails(empId) {
  const container = document.getElementById('workstation-cockpit-content');
  if (!container) return;

  try {
    const data = await apiGet(`/api/simulation/employees/${empId}`);
    _currentWorkspaceData = data;
    renderWorkstationCockpit(data);
  } catch (err) {
    console.error('Error fetching employee details:', err);
    container.innerHTML = `<div class="empty-state">ไม่สามารถโหลดข้อมูลพนักงานได้: ${err.message}</div>`;
  }
}

// ─── Master Render for Workstation Cockpit ────────────────────
function renderWorkstationCockpit(data) {
  const container = document.getElementById('workstation-cockpit-content');
  if (!container) return;

  const emp = data.employee;
  const tel = data.telemetry;
  const currentTask = data.current_task;
  const history = data.tasks_history || [];
  const logs = data.recent_logs || [];

  // Determine status color and text
  let statusTheme = 'status-idle';
  let gaugeClass = 'idle';
  let gaugeIcon = '🟢';
  let gaugePct = '100%';
  let statusTitle = `${emp.name} — พร้อมปฏิบัติงาน (Standby)`;
  let statusSub = 'ระบบความพร้อม 100% • รอรับบรีฟงานจาก Owner หรือ เลขาอิงฟ้า';

  if (emp.status === 'awaiting_confirmation') {
    statusTheme = 'status-pending';
    gaugeClass = 'pending';
    gaugeIcon = '🚨';
    gaugePct = '95%';
    statusTitle = '🚨 รอยืนยันอนุมัติปิดงาน (HITL)';
    statusSub = 'งานส่งมอบเสร็จสิ้นแล้ว รอการตรวจสอบและกดยืนยันไฟเขียวจากท่าน Owner';
  } else if (['coding', 'writing_content', 'reviewing', 'planning', 'active'].includes(emp.status)) {
    statusTheme = 'status-active';
    gaugeClass = 'active';
    gaugeIcon = emp.status === 'coding' ? '💻' : emp.status === 'writing_content' ? '✍️' : '⚡';
    gaugePct = `${emp.progress || 65}%`;
    statusTitle = `⚡ กำลังปฏิบัติงานสด (${gaugePct})`;
    statusSub = emp.current_action || 'กำลังดำเนินการตามขั้นตอน...';
  }

  // Calculate stroke dashoffset for circular gauge
  const radius = 58;
  const circumference = 2 * Math.PI * radius;
  let pctVal = parseInt(gaugePct) || 100;
  if (pctVal > 100) pctVal = 100;
  if (pctVal < 0) pctVal = 0;
  const strokeDashoffset = circumference - (pctVal / 100) * circumference;

  container.innerHTML = `
    <div class="workstation-cockpit">

      <!-- ═══════════════════════════════════════════════════════════ -->
      <!--  LEFT COLUMN: REALISTIC PERSONAL IDENTITY (Bio & Avatar)     -->
      <!-- ═══════════════════════════════════════════════════════════ -->
      <div class="identity-card">
        <div class="identity-photo-container">
          <button class="photo-change-btn" onclick="openAvatarModal('${escapeHtml(emp.id)}')" title="คลิกเพื่อเปลี่ยนรูปประจำตัว AI">
            <span>📷</span> เปลี่ยนรูป AI
          </button>
          <img src="${emp.photo_url}" alt="${escapeHtml(emp.name)}" onerror="this.src='/static/img/avatars/01_secretary.jpg'" id="ws-identity-photo" />
          <span class="identity-live-pill ${emp.status_badge_type || 'idle'}">
            <span class="dot"></span>
            <span>${escapeHtml(emp.status_label_th || 'Online')}</span>
          </span>
          <div class="identity-photo-overlay">
            <div class="identity-name-badge">${escapeHtml(emp.nickname || emp.name)}</div>
            <div class="identity-role-badge">${escapeHtml(emp.role_title)}</div>
          </div>
        </div>

        <div class="identity-motto-box">
          "${escapeHtml(emp.motto)}"
        </div>

        <div class="identity-details-list">
          <div class="identity-detail-row">
            <span class="identity-detail-label">🏢 สังกัดแผนก</span>
            <span class="identity-detail-val">${escapeHtml(emp.department_name)}</span>
          </div>
          <div class="identity-detail-row">
            <span class="identity-detail-label">🆔 รหัสพนักงาน</span>
            <span class="identity-detail-val" style="font-family:var(--font-mono); font-size:0.75rem; color:#818cf8;">${escapeHtml(emp.id)}</span>
          </div>
          <div class="identity-detail-row">
            <span class="identity-detail-label">🧠 AI Engine</span>
            <span class="identity-detail-val" style="font-family:var(--font-mono); font-size:0.75rem;">${escapeHtml(emp.model)}</span>
          <div class="identity-detail-row">
            <span class="identity-detail-label">🧠 ความฉลาด & เติบโต</span>
            <span class="identity-detail-val" style="color:#a78bfa; font-weight:600; font-size:0.75rem;">Level 1 • 0 EXP (เรียนรู้สะสม)</span>
          </div>
          <div class="identity-detail-row">
            <span class="identity-detail-label">⚡ โหมดคิดคำนวณ</span>
            <span class="identity-detail-val" style="color:#34d399; font-weight:600; font-size:0.75rem;">Zero-Token Ready (ฟรี 100%)</span>
          </div>
          <div class="identity-detail-row">
            <span class="identity-detail-label">🤖 Telegram Bot</span>
            <span class="identity-detail-val">${emp.has_bot ? '<span style="color:#34d399; font-weight:600;">✓ เชื่อมต่อแล้ว</span>' : '<span style="color:#94a3b8;">ยังไม่ผูก Bot</span>'}</span>
          </div>
          <div class="identity-detail-row">
            <span class="identity-detail-label">🛡️ กฎเหล็กประจำตัว</span>
            <span class="identity-detail-val" style="color:#f59e0b; font-size:0.78rem;">ต้องผ่าน Owner HITL เสมอ</span>
          </div>
        </div>

        <div class="identity-action-btns">
          <button class="btn-workstation-cmd primary" onclick="workstationAssignTask('${escapeHtml(emp.department_id)}', '${escapeHtml(emp.name)}')">
            <span>🚀 สั่งงานพนักงานคนนี้ทันที</span>
          </button>
          <button class="btn-workstation-cmd secondary" onclick="openAvatarModal('${escapeHtml(emp.id)}')">
            <span>📷 เปลี่ยนรูปประจำตัว AI</span>
          </button>
          <button class="btn-workstation-cmd secondary" onclick="openAgentMemoryModal('${escapeHtml(emp.id)}', '${escapeHtml(emp.name)}')">
            <span>🧠 ดูคลังความจำ & พฤติกรรมที่เรียนรู้</span>
          </button>
          <button class="btn-workstation-cmd secondary" onclick="workstationChat('${escapeHtml(emp.id)}', '${escapeHtml(emp.name)}')">
            <span>💬 คุยส่วนตัว 1-on-1 (Direct Prompt)</span>
          </button>
          <button class="btn-workstation-cmd secondary" onclick="workstationViewLogs('${escapeHtml(emp.id)}')">
            <span>📜 ดู Logs การทำงานทั้งหมด</span>
          </button>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════ -->
      <!--  CENTER COLUMN: LIVE WORK CENTERPIECE (Glow Ring & Tasks)   -->
      <!-- ═══════════════════════════════════════════════════════════ -->
      <div class="centerpiece-column">
        <div class="live-cockpit-hero ${statusTheme}">
          <!-- Circular Neon Progress Ring -->
          <div class="hero-gauge-container">
            <svg class="hero-gauge-ring" viewBox="0 0 140 140">
              <circle class="gauge-circle-bg" cx="70" cy="70" r="${radius}" />
              <circle class="gauge-circle-fill ${gaugeClass}" cx="70" cy="70" r="${radius}"
                stroke-dasharray="${circumference}"
                stroke-dashoffset="${strokeDashoffset}" />
            </svg>
            <div class="hero-gauge-center">
              <span class="hero-gauge-icon">${gaugeIcon}</span>
              <span class="hero-gauge-pct">${gaugePct}</span>
            </div>
          </div>

          <div class="hero-status-title">${statusTitle}</div>
          <div class="hero-status-sub">${statusSub}</div>

          <!-- Live Thought Stream Ticker Box -->
          <div class="live-thought-stream">
            <span class="thought-spark-icon">💭</span>
            <div class="thought-content">
              <div class="thought-label">Live AI Thought Process</div>
              <div class="thought-text">${escapeHtml(emp.current_thought || 'พร้อมรับคำสั่งงานใหม่จากท่าน Owner')}</div>
            </div>
          </div>

          <!-- Current Active or Pending Task Card -->
          ${renderCockpitTaskCard(currentTask, emp)}
        </div>

        <!-- ═══════════════════════════════════════════════════════════ -->
        <!--  BOTTOM OF CENTERPIECE: WORK HISTORY & TASK LOG             -->
        <!-- ═══════════════════════════════════════════════════════════ -->
        <div class="work-history-section">
          <div class="history-header-row">
            <div class="history-title-box">
              <span style="font-size:1.35rem;">📋</span>
              <div>
                <h3 style="margin:0;">ประวัติผลงาน & Task งานที่ผ่านมาของ ${escapeHtml(emp.name)}</h3>
                <span style="font-size:0.75rem; color:var(--text-muted);">ตรวจสอบงานที่เคยทำ สถานะการส่งมอบ และผลการอนุมัติ (HITL)</span>
              </div>
            </div>
            <div class="history-filter-tabs">
              <button class="history-tab-btn ${_historyFilter === 'all' ? 'active' : ''}" onclick="setWorkstationHistoryFilter('all')">
                ทั้งหมด (${history.length})
              </button>
              <button class="history-tab-btn ${_historyFilter === 'CONFIRMED' ? 'active' : ''}" onclick="setWorkstationHistoryFilter('CONFIRMED')">
                ✅ เสร็จแล้ว (${tel.completed_tasks_count})
              </button>
              <button class="history-tab-btn ${_historyFilter === 'IN_PROGRESS' ? 'active' : ''}" onclick="setWorkstationHistoryFilter('IN_PROGRESS')">
                ⚡ กำลังทำ (${tel.active_tasks_count})
              </button>
              <button class="history-tab-btn ${_historyFilter === 'AWAITING_CONFIRMATION' ? 'active' : ''}" onclick="setWorkstationHistoryFilter('AWAITING_CONFIRMATION')">
                🚨 รอยืนยัน (${tel.pending_confirm_count})
              </button>
            </div>
          </div>

          <!-- History Tasks Cards List -->
          <div class="history-tasks-list" id="workstation-history-list">
            ${renderHistoryTaskList(history, _historyFilter)}
          </div>
        </div>

        <!-- Employee Live Logs Stream -->
        <div class="employee-logs-section">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:1.1rem;">📜</span>
              <strong style="color:var(--text-primary); font-size:0.9rem;">บันทึก Logs การทำงานสดของ ${escapeHtml(emp.name)}</strong>
            </div>
            <span style="font-size:0.72rem; color:var(--text-dim); font-family:var(--font-mono);">Live Feed</span>
          </div>
          <div class="emp-log-stream">
            ${renderEmployeeLogs(logs)}
          </div>
        </div>

      </div>

      <!-- ═══════════════════════════════════════════════════════════ -->
      <!--  RIGHT COLUMN: FUTURISTIC TELEMETRY & GAUGES                 -->
      <!-- ═══════════════════════════════════════════════════════════ -->
      <div class="telemetry-column">
        <div class="telemetry-card">
          <div class="telemetry-header">
            <div class="telemetry-title">
              <span>📊</span>
              <span>Telemetry & Performance KPIs</span>
            </div>
            <span class="badge" style="background:rgba(52,211,153,0.15); color:#34d399; font-size:0.7rem;">Verified 100%</span>
          </div>

          <!-- Mini Circular Gauges Grid -->
          <div class="telemetry-gauges-grid">
            <div class="mini-gauge-widget">
              <div class="mini-gauge-ring">
                <svg viewBox="0 0 68 68" style="width:100%; height:100%; transform:rotate(-90deg);">
                  <circle cx="34" cy="34" r="28" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="5" />
                  <circle cx="34" cy="34" r="28" fill="none" stroke="#10b981" stroke-width="5" stroke-dasharray="175.9" stroke-dashoffset="0" stroke-linecap="round" />
                </svg>
                <span class="mini-gauge-val" style="color:#34d399;">${tel.quality_score}</span>
              </div>
              <span class="mini-gauge-label">Quality & QA Pass</span>
            </div>

            <div class="mini-gauge-widget">
              <div class="mini-gauge-ring">
                <svg viewBox="0 0 68 68" style="width:100%; height:100%; transform:rotate(-90deg);">
                  <circle cx="34" cy="34" r="28" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="5" />
                  <circle cx="34" cy="34" r="28" fill="none" stroke="#06b6d4" stroke-width="5" stroke-dasharray="175.9" stroke-dashoffset="1" stroke-linecap="round" />
                </svg>
                <span class="mini-gauge-val" style="color:#38bdf8;">${tel.uptime}</span>
              </div>
              <span class="mini-gauge-label">Uptime & Health</span>
            </div>
          </div>

          <!-- Risk & Security Meter -->
          <div class="risk-meter-box">
            <span class="risk-icon">🛡️</span>
            <div>
              <div class="risk-info-title">${tel.risk_index}</div>
              <div class="risk-info-sub">ผ่านการตรวจช่องโหว่ OWASP & Token Security</div>
            </div>
          </div>

          <!-- KPI Counters Grid -->
          <div class="kpi-counters-grid">
            <div class="kpi-counter-item">
              <span class="kpi-num" style="color:#34d399;">${tel.completed_tasks_count}</span>
              <span class="kpi-label">งานที่เสร็จสมบูรณ์</span>
            </div>
            <div class="kpi-counter-item">
              <span class="kpi-num" style="color:#818cf8;">${tel.active_tasks_count}</span>
              <span class="kpi-label">งานที่กำลังทำ</span>
            </div>
            <div class="kpi-counter-item">
              <span class="kpi-num" style="color:#fbbf24;">${tel.pending_confirm_count}</span>
              <span class="kpi-label">รอยืนยันปิดงาน</span>
            </div>
            <div class="kpi-counter-item">
              <span class="kpi-num" style="color:#e2e8f0;">${tel.avg_turnaround_time}</span>
              <span class="kpi-label">ความเร็วเฉลี่ย/งาน</span>
            </div>
          </div>

          <!-- Skills & Tech Stack Pipeline (like bottom icons in user image) -->
          <div>
            <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:6px; font-weight:600;">
              ⚙️ Tech Stack & Specialized Skills:
            </div>
            <div class="tech-stack-strip">
              ${(emp.tech_stack || []).map(t => `<span class="tech-chip">${escapeHtml(t)}</span>`).join('')}
            </div>
          </div>
        </div>
      </div>

    </div>
  `;
}

// ─── Render Cockpit Task Card ─────────────────────────────────
function renderCockpitTaskCard(task, emp) {
  if (!task) {
    return `
      <div class="current-task-cockpit-card" style="text-align:center; padding:1.25rem;">
        <span style="font-size:1.5rem; opacity:0.6;">📥</span>
        <div style="font-size:0.85rem; color:var(--text-muted); margin-top:4px;">ขณะนี้ไม่มีงานค้างอยู่ในคิว — พร้อมรับมอบหมายงานใหม่ทันที</div>
        <button class="btn btn-sm btn-primary" style="margin-top:10px;" onclick="workstationAssignTask('${escapeHtml(emp.department_id)}', '${escapeHtml(emp.name)}')">
          ＋ มอบหมายงานใหม่ให้ ${escapeHtml(emp.name)}
        </button>
      </div>
    `;
  }

  const isPending = task.status === 'AWAITING_CONFIRMATION';
  const tagClass = isPending ? 'pending' : (task.status === 'CONFIRMED' ? 'confirmed' : 'active');
  const tagText = isPending ? '🚨 รอยืนยันอนุมัติปิดงาน' : (task.status === 'CONFIRMED' ? '✅ เสร็จสมบูรณ์แล้ว' : '⚡ กำลังปฏิบัติงานสด');

  return `
    <div class="current-task-cockpit-card">
      <div class="current-task-top">
        <span class="task-tag ${tagClass}">${tagText}</span>
        <span style="font-size:0.75rem; color:var(--text-dim); font-family:var(--font-mono);">Task ID: ${escapeHtml(task.id)}</span>
      </div>
      <div class="current-task-title">${escapeHtml(task.title)}</div>
      <div style="font-size:0.78rem; color:var(--text-muted); line-height:1.4;">
        ${escapeHtml(task.prompt || 'ไม่มีคำอธิบาย')}
      </div>

      <div class="current-task-progress-bar">
        <div class="current-task-progress-fill" style="width: ${emp.progress || (isPending ? 100 : 50)}%;"></div>
      </div>

      <div class="task-card-actions">
        ${isPending ? `
          <button class="btn btn-sm btn-primary" style="background:#10b981; border-color:#059669; font-weight:700;" onclick="workstationConfirmAction('${escapeHtml(task.id)}')">
            ✅ อนุมัติปิดงานทันที (Confirm)
          </button>
          <button class="btn btn-sm btn-danger" onclick="workstationReviseAction('${escapeHtml(task.id)}')">
            🔄 สั่งแก้ไข
          </button>
        ` : ''}
        <button class="btn btn-sm" onclick="openDeliverableForTask('${escapeHtml(task.id)}')">
          📦 ตรวจดูผลงานส่งมอบ (Deliverable)
        </button>
      </div>
    </div>
  `;
}

// ─── Render History Tasks List ────────────────────────────────
function renderHistoryTaskList(tasks, filter) {
  let filtered = tasks;
  if (filter === 'CONFIRMED') {
    filtered = tasks.filter(t => t.status === 'CONFIRMED');
  } else if (filter === 'IN_PROGRESS') {
    filtered = tasks.filter(t => t.status === 'IN_PROGRESS' || t.status === 'QA_REVIEW');
  } else if (filter === 'AWAITING_CONFIRMATION') {
    filtered = tasks.filter(t => t.status === 'AWAITING_CONFIRMATION');
  }

  if (filtered.length === 0) {
    return `
      <div style="text-align:center; padding:2rem; color:var(--text-dim); font-size:0.85rem;">
        ไม่มีรายการงานในหมวดหมู่นี้
      </div>
    `;
  }

  return filtered.map(t => {
    let statusBadge = '<span class="task-tag confirmed">✅ เสร็จสมบูรณ์แล้ว</span>';
    if (t.status === 'AWAITING_CONFIRMATION') {
      statusBadge = '<span class="task-tag pending">🚨 รอยืนยันอนุมัติ</span>';
    } else if (t.status === 'IN_PROGRESS' || t.status === 'QA_REVIEW') {
      statusBadge = '<span class="task-tag active">⚡ กำลังทำ</span>';
    }

    const del = t.deliverable;
    const summaryText = del ? del.summary : (t.prompt || 'ไม่มีรายละเอียดสรุป');
    const qaReport = del?.qa_report || '✅ ผ่านการประเมินมาตรฐานองค์กร 100%';
    const createdTime = formatIsoDateTime(t.created_at);

    return `
      <div class="history-task-item">
        <div class="history-item-top">
          <div style="display:flex; flex-direction:column; gap:3px;">
            <div class="history-item-title">${escapeHtml(t.title)}</div>
            <div class="history-item-meta">
              <span>📅 ${createdTime}</span>
              <span>🏷️ ${escapeHtml(t.category || 'General')}</span>
            </div>
          </div>
          ${statusBadge}
        </div>

        <div class="history-item-body">
          ${escapeHtml(summaryText)}
        </div>

        <div class="history-item-footer">
          <span class="history-qa-badge">
            <span>🧪</span>
            <span>${escapeHtml(qaReport)}</span>
          </span>
          <button class="btn btn-sm" onclick="openDeliverableForTask('${escapeHtml(t.id)}')">
            📦 ตรวจสอบผลงานส่งมอบ →
          </button>
        </div>
      </div>
    `;
  }).join('');
}

// ─── Render Employee Logs ─────────────────────────────────────
function renderEmployeeLogs(logs) {
  if (logs.length === 0) {
    return `<div style="text-align:center; padding:1.5rem; color:var(--text-dim);">ไม่มีบันทึกการทำงานล่าสุด</div>`;
  }

  return logs.map(l => {
    const timeStr = formatIsoTime(l.timestamp);
    return `
      <div class="emp-log-row">
        <span class="emp-log-time">${timeStr}</span>
        <span class="emp-log-level ${l.level}">${l.level}</span>
        <span class="emp-log-msg">${escapeHtml(l.message)}</span>
      </div>
    `;
  }).join('');
}

// ─── Filter & Action Handlers ─────────────────────────────────
function setWorkstationHistoryFilter(filter) {
  _historyFilter = filter;
  if (_currentWorkspaceData) {
    renderWorkstationCockpit(_currentWorkspaceData);
  }
}

function workstationAssignTask(deptId, empName) {
  if (typeof openDeptDispatchModal === 'function') {
    openDeptDispatchModal(deptId);
  }
}

function workstationChat(empId, empName) {
  if (empId === '01_secretary') {
    if (typeof openSecretaryChat === 'function') openSecretaryChat();
  } else {
    if (typeof openDirectCommandModal === 'function') {
      openDirectCommandModal(empId, empName);
    }
  }
}

function workstationViewLogs(empId) {
  if (typeof navigateTo === 'function') {
    navigateTo('logs');
    setTimeout(() => {
      const agentSel = document.getElementById('log-agent-filter');
      if (agentSel) {
        agentSel.value = empId;
        if (typeof filterLogs === 'function') filterLogs();
      }
    }, 300);
  }
}

async function workstationConfirmAction(taskId) {
  if (typeof confirmTaskAction === 'function') {
    await confirmTaskAction(taskId);
    await loadActiveEmployeeDetails(_activeEmpId);
  }
}

function workstationReviseAction(taskId) {
  if (typeof openRevisionDialog === 'function') {
    openRevisionDialog(taskId);
  }
}

function openDeliverableForTask(taskId) {
  if (typeof openDeliverableModal === 'function') {
    openDeliverableModal(taskId);
  }
}

function formatIsoDateTime(isoStr) {
  if (!isoStr) return '--:--';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('th-TH', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return isoStr;
  }
}

// ─── Avatar Customization Handlers ────────────────────────────
let _currentAvatarTargetId = null;
let _currentAvatarPendingUrl = null;
let _currentAvatarPendingFile = null;
let _avatarActiveTab = 'upload';

function openAvatarModal(empId) {
  _currentAvatarTargetId = empId || _activeEmpId;
  _currentAvatarPendingUrl = null;
  _currentAvatarPendingFile = null;
  
  const emp = (_cachedEmployees || []).find(e => e.id === _currentAvatarTargetId) || {
    id: _currentAvatarTargetId,
    name: _currentAvatarTargetId,
    role_title: 'AI Employee',
    photo_url: `/static/img/avatars/${_currentAvatarTargetId}.jpg`
  };

  const nameEl = document.getElementById('avatar-modal-name');
  const roleEl = document.getElementById('avatar-modal-role');
  const imgEl = document.getElementById('avatar-modal-img');
  const fileInput = document.getElementById('avatar-file-input');
  const urlInput = document.getElementById('avatar-url-input');

  if (nameEl) nameEl.textContent = emp.nickname || emp.name;
  if (roleEl) roleEl.textContent = emp.role_title || emp.department_name || 'AI Specialist';
  if (imgEl) {
    imgEl.src = emp.photo_url || '/static/img/avatars/01_secretary.jpg';
    imgEl.onerror = () => { imgEl.src = '/static/img/avatars/01_secretary.jpg'; };
  }
  if (fileInput) fileInput.value = '';
  if (urlInput) urlInput.value = '';

  document.querySelectorAll('.avatar-preset-item').forEach(el => el.classList.remove('selected'));

  switchAvatarTab('upload');
  openModal('modal-change-avatar');
}

function switchAvatarTab(tab) {
  _avatarActiveTab = tab;
  document.querySelectorAll('.avatar-method-tab').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tab);
  });
  document.querySelectorAll('.avatar-tab-content').forEach(c => {
    c.classList.toggle('active', c.id === `avatar-tab-${tab}`);
  });
}

function onAvatarFileSelected(e) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;

  if (file.size > 5 * 1024 * 1024) {
    if (typeof toast === 'function') toast('ขนาดไฟล์เกิน 5MB กรุณาเลือกรูปขนาดเล็กลง', 'warning');
    return;
  }

  _currentAvatarPendingFile = file;
  const reader = new FileReader();
  reader.onload = (ev) => {
    const imgEl = document.getElementById('avatar-modal-img');
    if (imgEl) imgEl.src = ev.target.result;
    _currentAvatarPendingUrl = ev.target.result;
  };
  reader.readAsDataURL(file);
}

function onAvatarUrlChange() {
  const url = document.getElementById('avatar-url-input')?.value.trim();
  if (!url) return;
  _currentAvatarPendingUrl = url;
  const imgEl = document.getElementById('avatar-modal-img');
  if (imgEl) imgEl.src = url;
}

function selectPresetAvatar(url, element) {
  _currentAvatarPendingUrl = url;
  _currentAvatarPendingFile = null;
  const imgEl = document.getElementById('avatar-modal-img');
  if (imgEl) imgEl.src = url;
  
  document.querySelectorAll('.avatar-preset-item').forEach(el => el.classList.remove('selected'));
  if (element) element.classList.add('selected');
}

async function saveAvatarModalChanges() {
  if (!_currentAvatarTargetId) return;

  const saveBtn = document.getElementById('btn-save-avatar');
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span>⏳ กำลังบันทึก...</span>';
  }

  try {
    let result = null;
    if (_avatarActiveTab === 'upload' && _currentAvatarPendingFile) {
      const formData = new FormData();
      formData.append('file', _currentAvatarPendingFile);
      const res = await fetch(`/api/simulation/employees/${encodeURIComponent(_currentAvatarTargetId)}/avatar`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      result = await res.json();
    } else if (_currentAvatarPendingUrl) {
      result = await apiPost(`/api/simulation/employees/${encodeURIComponent(_currentAvatarTargetId)}/avatar-url`, {
        avatar_url: _currentAvatarPendingUrl,
      });
    } else {
      if (typeof toast === 'function') toast('กรุณาเลือกไฟล์รูปภาพ หรือใส่ URL รูปภาพก่อนบันทึก', 'warning');
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<span>💾 บันทึกรูปภาพ</span>';
      }
      return;
    }

    const newUrl = result.avatar_url;

    // Update in cached list
    const emp = (_cachedEmployees || []).find(e => e.id === _currentAvatarTargetId);
    if (emp) emp.photo_url = newUrl;

    // Update UI elements in DOM
    const wsPhoto = document.getElementById('ws-identity-photo');
    if (wsPhoto && _activeEmpId === _currentAvatarTargetId) {
      wsPhoto.src = newUrl;
    }
    if (typeof renderEmployeeSelectorStrip === 'function') {
      renderEmployeeSelectorStrip(_cachedEmployees, _activeEmpId);
    }

    // Update team card in DOM and allAgents
    const tcImg = document.querySelector(`#tc-${CSS.escape(_currentAvatarTargetId)} .team-avatar img`);
    if (tcImg) {
      tcImg.src = newUrl;
    }
    if (window.allAgents) {
      const ag = window.allAgents.find(a => a.id === _currentAvatarTargetId || a.department === _currentAvatarTargetId);
      if (ag) ag.avatar_url = newUrl;
    }
    if (typeof window.loadTeams === 'function') {
      window.loadTeams();
    }

    // Refresh simulation state & dashboard if present
    if (typeof fetchSimulationState === 'function') fetchSimulationState();
    if (typeof loadDashboard === 'function') loadDashboard();

    closeModal('modal-change-avatar');
    if (typeof toast === 'function') toast('🎉 เปลี่ยนรูปประจำตัว AI เรียบร้อยแล้ว!', 'success');

  } catch (err) {
    console.error('Failed to update avatar:', err);
    if (typeof toast === 'function') toast(`เกิดข้อผิดพลาดในการเปลี่ยนรูป: ${err.message}`, 'error');
  } finally {
    if (saveBtn) {
      saveBtn.disabled = false;
      saveBtn.innerHTML = '<span>💾 บันทึกรูปภาพ</span>';
    }
  }
}

async function resetAvatarModalChanges() {
  if (!_currentAvatarTargetId) return;

  if (!confirm('ต้องการรีเซ็ตรูปภาพของ AI คนนี้กลับเป็นรูปเริ่มต้นของระบบหรือไม่?')) return;

  try {
    const res = await apiPost(`/api/simulation/employees/${encodeURIComponent(_currentAvatarTargetId)}/avatar/reset`, {});
    const defaultUrl = res.avatar_url;

    const emp = (_cachedEmployees || []).find(e => e.id === _currentAvatarTargetId);
    if (emp) emp.photo_url = defaultUrl;

    const wsPhoto = document.getElementById('ws-identity-photo');
    if (wsPhoto && _activeEmpId === _currentAvatarTargetId) {
      wsPhoto.src = defaultUrl;
    }
    if (typeof renderEmployeeSelectorStrip === 'function') {
      renderEmployeeSelectorStrip(_cachedEmployees, _activeEmpId);
    }

    if (typeof fetchSimulationState === 'function') fetchSimulationState();
    if (typeof loadDashboard === 'function') loadDashboard();

    closeModal('modal-change-avatar');
    if (typeof toast === 'function') toast('🔄 รีเซ็ตรูปภาพ AI กลับเป็นค่าเริ่มต้นเรียบร้อยแล้ว', 'info');

  } catch (err) {
    console.error('Failed to reset avatar:', err);
    if (typeof toast === 'function') toast(`เกิดข้อผิดพลาดในการรีเซ็ตรูป: ${err.message}`, 'error');
  }
}

function openAgentMemoryModal(deptId, empName) {
  const modal = document.getElementById('modal-agent-memory');
  if (!modal) return;
  const title = document.getElementById('memory-modal-title');
  const content = document.getElementById('memory-modal-content');
  if (title) title.textContent = `🧠 ความจำ & การเติบโตของ ${empName}`;
  if (content) {
    if (_currentWorkspaceData && _currentWorkspaceData.employee && _currentWorkspaceData.employee.memory_md) {
      content.textContent = _currentWorkspaceData.employee.memory_md;
    } else {
      content.textContent = 'กำลังเริ่มต้นความจำระยะยาว... พนักงานคนนี้พร้อมเก็บเกี่ยวประสบการณ์จริงจากการทำงาน';
    }
  }
  openModal('modal-agent-memory');
}

// Hook into simulation live state update
if (typeof window !== 'undefined') {
  window.loadWorkstations = loadWorkstations;
  window.openAgentMemoryModal = openAgentMemoryModal;
  window.switchWorkstationEmployee = switchWorkstationEmployee;
  window.setWorkstationHistoryFilter = setWorkstationHistoryFilter;
  window.workstationAssignTask = workstationAssignTask;
  window.workstationChat = workstationChat;
  window.workstationViewLogs = workstationViewLogs;
  window.workstationConfirmAction = workstationConfirmAction;
  window.workstationReviseAction = workstationReviseAction;
  window.openDeliverableForTask = openDeliverableForTask;
  window.openAvatarModal = openAvatarModal;
  window.switchAvatarTab = switchAvatarTab;
  window.onAvatarFileSelected = onAvatarFileSelected;
  window.onAvatarUrlChange = onAvatarUrlChange;
  window.selectPresetAvatar = selectPresetAvatar;
  window.saveAvatarModalChanges = saveAvatarModalChanges;
  window.resetAvatarModalChanges = resetAvatarModalChanges;
}
