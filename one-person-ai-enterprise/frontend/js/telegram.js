/* ═══════════════════════════════════════
   telegram.js — Telegram Clean Room Architecture & Monitor
   ═══════════════════════════════════════ */

// ─── Load Telegram Page ──────────────────────────────────
async function loadTelegram() {
  await Promise.all([
    loadTelegramRoomStatus(),
    loadTelegramVerifications(),
  ]);
  setTelegramWebhookUrl();
}

async function loadTelegramRoomStatus() {
  try {
    const rooms = await apiFetch('/api/telegram/rooms');

    // 1. Direct Chat (1-on-1: Owner ↔ เลขา)
    const directEl = document.getElementById('direct-room-status');
    if (directEl) {
      directEl.innerHTML = rooms.direct_chat?.configured
        ? `<div style="font-size:12px;color:var(--color-success);padding:0 1.5rem 1rem">
             ✅ เชื่อมต่อแชทส่วนตัวแล้ว &nbsp; <code style="font-size:11px;color:var(--color-text-muted)">Chat ID: ${rooms.direct_chat.id}</code>
           </div>`
        : `<div style="font-size:12px;color:var(--color-warning);padding:0 1.5rem 1rem">
             ⚠️ ยังไม่ได้ใส่ Direct Chat ID — ไปที่ <a href="#/settings" style="color:var(--brand-400)">Settings</a>
           </div>`;
    }

    // 2. Executive Boardroom (Owner + เลขา + PMs)
    const adminEl = document.getElementById('admin-room-status');
    if (adminEl) {
      adminEl.innerHTML = rooms.executive_room?.configured
        ? `<div style="font-size:12px;color:var(--color-success);padding:0 1.5rem 1rem">
             ✅ เชื่อมต่อห้องผู้บริหารแล้ว &nbsp; <code style="font-size:11px;color:var(--color-text-muted)">Chat ID: ${rooms.executive_room.id}</code>
           </div>`
        : `<div style="font-size:12px;color:var(--color-warning);padding:0 1.5rem 1rem">
             ⚠️ ยังไม่ได้ใส่ Executive Chat ID — ไปที่ <a href="#/settings" style="color:var(--brand-400)">Settings</a>
           </div>`;
    }

    // 3. Department Working Rooms List
    renderDepartmentRoomsList(rooms.department_rooms || {});

    const tgBadge = document.getElementById('skype-badge') || document.getElementById('telegram-badge');
    if (tgBadge) {
      tgBadge.style.display = rooms.bot_configured ? 'none' : '';
      if (!rooms.bot_configured) tgBadge.textContent = '!';
    }
  } catch (e) { /* ignore */ }
}

function renderDepartmentRoomsList(departmentRooms) {
  const container = document.getElementById('department-rooms-list');
  if (!container) return;

  const entries = Object.entries(departmentRooms);
  if (!entries.length) {
    container.innerHTML = `
      <div class="empty-state" style="padding:1.5rem 0;">
        <span>🏢</span>
        <p>ยังไม่มีห้องทำงานแผนก</p>
        <button class="btn btn-sm btn-primary" onclick="openCreateRoomModal()">＋ สร้างห้องแผนกแรก</button>
      </div>`;
    return;
  }

  container.innerHTML = entries.map(([deptId, info]) => {
    const isConfigured = info.configured;
    return `
      <div class="dept-room-card" style="display:flex; justify-content:space-between; align-items:center; background:rgba(255,255,255,0.03); border:1px solid var(--color-border); border-radius:10px; padding:0.8rem 1.2rem;">
        <div style="display:flex; flex-direction:column; gap:3px;">
          <div style="font-size:14px; font-weight:600; color:var(--color-text); display:flex; align-items:center; gap:8px;">
            <span>🏢 ${esc(info.name || deptId)}</span>
            <code style="font-size:11px; color:var(--brand-400); font-weight:normal;">(${esc(deptId)})</code>
          </div>
          <div style="font-size:12px; color:var(--color-text-muted);">
            👤 <strong>ดูแลโดย:</strong> ${esc(info.pm_name || 'PM ประจำแผนก')}
          </div>
          <div style="font-size:11px; margin-top:2px;">
            ${isConfigured
              ? `<span style="color:var(--color-success)">✅ Chat ID: <code style="color:var(--color-text)">${esc(info.ops_chat_id)}</code></span>`
              : `<span style="color:var(--color-warning)">⚠️ ยังไม่ตั้ง Chat ID เฉพาะ</span>`}
          </div>
        </div>

        <div style="display:flex; gap:6px; align-items:center;">
          <button class="btn btn-sm btn-primary" onclick="inspectDepartmentWorkspace('${esc(deptId)}', '${esc(info.name)}', '${esc(info.pm_name)}')" title="เข้าดูการทำงานของลูกทีม">
            🔍 เข้าดูการทำงานของลูกทีม
          </button>
          <button class="btn btn-sm btn-danger" onclick="deleteDepartmentRoom('${esc(deptId)}', '${esc(info.name)}')" title="ยุบแผนก / ลบห้อง">
            🗑️ ยุบแผนก
          </button>
        </div>
      </div>
    `;
  }).join('');
}


// ─── Room Creation Modal ──────────────────────────────────
function openCreateRoomModal() {
  const modal = document.getElementById('create-room-modal');
  if (modal) {
    document.getElementById('create-room-form').reset();
    modal.classList.add('open');
  }
}

function closeCreateRoomModal() {
  const modal = document.getElementById('create-room-modal');
  if (modal) modal.classList.remove('open');
}

async function submitCreateRoomForm(event) {
  event.preventDefault();
  const btn = document.getElementById('btn-submit-create-room');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinning">⏳</span> กำลังสร้าง...';

  const name = document.getElementById('new-room-name').value.trim();
  const pmName = document.getElementById('new-room-pm').value.trim();
  const chatId = document.getElementById('new-room-chat-id').value.trim();

  try {
    const resp = await apiFetch('/api/telegram/rooms', {
      method: 'POST',
      body: JSON.stringify({ name, pm_name: pmName, chat_id: chatId }),
    });

    showToast(`✅ สร้างห้องแผนก "${name}" เรียบร้อย`, 'success');
    closeCreateRoomModal();

    await loadTelegramRoomStatus();
  } catch (e) {
    showToast(`สร้างห้องแผนกไม่สำเร็จ: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '💾 สร้างห้องแผนก';
  }
}

// ─── Dissolve Department Room (ยุบแผนก / ลบห้อง) ───────────
async function deleteDepartmentRoom(deptId, deptName) {
  if (!confirm(`⚠️ ยืนยันการยุบแผนก "${deptName}" (${deptId})?\n\nโฟลเดอร์และคอนฟิกของแผนกนี้จะถูกลบออกจากระบบ`)) {
    return;
  }

  try {
    await apiFetch(`/api/telegram/rooms/${deptId}`, { method: 'DELETE' });
    showToast(`🗑️ ยุบแผนก "${deptName}" เรียบร้อย`, 'success');
    await loadTelegramRoomStatus();
  } catch (e) {
    showToast(`ยุบแผนกไม่สำเร็จ: ${e.message}`, 'error');
  }
}

// ─── Verification List ────────────────────────────────────
async function loadTelegramVerifications() {
  try {
    const verifications = await apiFetch('/api/telegram/verifications');
    renderTelegramVerifications(verifications);
  } catch (e) {
    const list = document.getElementById('verifications-list');
    if (list) {
      list.innerHTML = '<div class="empty-state"><p>โหลดรายการไม่สำเร็จ</p></div>';
    }
  }
}

function renderTelegramVerifications(verifications) {
  const container = document.getElementById('verifications-list');
  if (!container) return;

  if (!verifications || !verifications.length) {
    container.innerHTML = `
      <div class="empty-state">
        <span>✅</span>
        <p>ไม่มีรายการรอยืนยัน</p>
      </div>`;
    return;
  }

  container.innerHTML = verifications.map(v => `
    <div class="verification-item" id="verify-${esc(v.id)}">
      <div style="font-size:11px;color:var(--color-text-muted);margin-bottom:6px">
        ${formatDate(v.created_at)} &nbsp; | &nbsp;
        <span style="color:${statusColor(v.status)}">${statusLabel(v.status)}</span>
      </div>
      <div class="verification-summary">${esc(v.summary || v.original_message || '')}</div>
      ${v.status === 'awaiting_owner' ? `
        <div class="verification-actions">
          <button class="btn btn-success" onclick="confirmTelegramVerification('${esc(v.id)}', true)">
            ✅ ยืนยัน
          </button>
          <button class="btn btn-danger" onclick="confirmTelegramVerification('${esc(v.id)}', false)">
            ❌ ยกเลิก
          </button>
        </div>` : ''}
    </div>
  `).join('');
}

async function confirmTelegramVerification(verificationId, confirmed) {
  try {
    await apiFetch(`/api/telegram/verify/${verificationId}`, {
      method: 'POST',
      body: JSON.stringify({ confirmed }),
    });

    if (confirmed) {
      showToast('✅ ยืนยันแล้ว! กำลังส่งแผนงานให้ PM...', 'success');
    } else {
      showToast('❌ ยกเลิกคำสั่งเรียบร้อย', 'warning');
    }

    await loadTelegramVerifications();
  } catch (e) {
    showToast(`เกิดข้อผิดพลาด: ${e.message}`, 'error');
  }
}

// ─── Simulator ────────────────────────────────────────────
async function simulateTelegramMessage() {
  const textarea = document.getElementById('simulate-text');
  const text = textarea ? textarea.value.trim() : '';
  if (!text) {
    showToast('กรุณากรอกข้อความคำสั่งก่อน', 'warning');
    return;
  }

  const btn = document.getElementById('btn-simulate');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinning">⏳</span> กำลังประมวลผล...';
  }

  const resultEl = document.getElementById('simulate-result');
  if (resultEl) resultEl.style.display = 'none';

  try {
    const result = await apiFetch('/api/telegram/simulate', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });

    if (resultEl) {
      resultEl.style.display = 'block';
      resultEl.innerHTML = `<strong>ผลลัพธ์การจำลอง:</strong>\n${JSON.stringify(result, null, 2)}`;
    }

    if (result.simulated) {
      showToast('ส่งคำสั่งจำลองสำเร็จ', 'success');
      setTimeout(loadTelegramVerifications, 1000);
    }
  } catch (e) {
    if (resultEl) {
      resultEl.style.display = 'block';
      resultEl.innerHTML = `<span style="color:var(--color-error)">เกิดข้อผิดพลาด: ${e.message}</span>`;
    }
    showToast(`เกิดข้อผิดพลาด: ${e.message}`, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '📨 ส่งคำสั่งจำลอง';
    }
  }
}

// ─── Webhook URL ──────────────────────────────────────────
function setTelegramWebhookUrl() {
  const urlEl = document.getElementById('webhook-url-display');
  if (urlEl) {
    urlEl.textContent = `http://YOUR_SERVER_IP:8000/api/telegram/webhook`;
  }
}

function copyTelegramWebhookUrl() {
  const url = document.getElementById('webhook-url-display')?.textContent || '';
  navigator.clipboard.writeText(url).then(() => {
    showToast('คัดลอก Webhook URL สำเร็จ', 'success');
  }).catch(() => {
    showToast('คัดลอกไม่สำเร็จ กรุณาคัดลอกเอง', 'warning');
  });
}


async function inspectDepartmentWorkspace(deptId, deptName, pmName) {
  showToast(`🔍 กำลังเปิดกระดานการทำงานของลูกทีมแผนก ${deptName}...`, 'info');
  try {
    const logFilter = document.getElementById('log-filter-agent');
    if (logFilter) logFilter.value = deptId;
    navigateTo('logs');
    if (typeof loadLogs !== 'undefined') loadLogs();
  } catch (e) {
    showToast('เปิดกระดานการทำงานไม่สำเร็จ: ' + e.message, 'error');
  }
}

