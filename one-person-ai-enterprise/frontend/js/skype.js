/* ═══════════════════════════════════════
   skype.js — Skype Room Monitor & Simulator
   ═══════════════════════════════════════ */

// ─── Load Skype Page ──────────────────────────────────────
async function loadSkype() {
  await Promise.all([
    loadRoomStatus(),
    loadVerifications(),
  ]);
  setWebhookUrl();
}

async function loadRoomStatus() {
  try {
    const rooms = await apiFetch('/api/skype/rooms');

    document.getElementById('admin-room-status').innerHTML = rooms.admin_room?.configured
      ? `<div style="font-size:12px;color:var(--color-success);padding:0 1.5rem 1rem">
           ✅ เชื่อมต่อแล้ว &nbsp; <code style="font-size:11px;color:var(--color-text-muted)">${rooms.admin_room.id || ''}</code>
         </div>`
      : `<div style="font-size:12px;color:var(--color-warning);padding:0 1.5rem 1rem">
           ⚠️ ยังไม่ตั้งค่า Room ID — ไปที่ <a href="#/settings" style="color:var(--brand-400)">Settings</a>
         </div>`;

    document.getElementById('ops-room-status').innerHTML = rooms.ops_room?.configured
      ? `<div style="font-size:12px;color:var(--color-success);padding:0 1.5rem 1rem">
           ✅ เชื่อมต่อแล้ว &nbsp; <code style="font-size:11px;color:var(--color-text-muted)">${rooms.ops_room.id || ''}</code>
         </div>`
      : `<div style="font-size:12px;color:var(--color-warning);padding:0 1.5rem 1rem">
           ⚠️ ยังไม่ตั้งค่า Room ID — ไปที่ <a href="#/settings" style="color:var(--brand-400)">Settings</a>
         </div>`;

    // อัปเดต skype badge
    const skypeConfigured = rooms.admin_room?.configured && rooms.ops_room?.configured;
    const skypeBadge = document.getElementById('skype-badge');
    if (!skypeConfigured) {
      skypeBadge.style.display = '';
      skypeBadge.textContent = '!';
    } else {
      skypeBadge.style.display = 'none';
    }
  } catch (e) { /* ignore */ }
}

async function loadVerifications() {
  try {
    const verifications = await apiFetch('/api/skype/verifications');
    renderVerifications(verifications);
  } catch (e) {
    document.getElementById('verifications-list').innerHTML =
      '<div class="empty-state"><p>โหลดไม่สำเร็จ</p></div>';
  }
}

function renderVerifications(verifications) {
  const container = document.getElementById('verifications-list');

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
          <button class="btn btn-success" onclick="confirmVerification('${esc(v.id)}', true)">
            ✅ ยืนยัน
          </button>
          <button class="btn btn-danger" onclick="confirmVerification('${esc(v.id)}', false)">
            ❌ ยกเลิก
          </button>
        </div>` : ''}
    </div>
  `).join('');
}

async function confirmVerification(verificationId, confirmed) {
  try {
    const result = await apiFetch(`/api/skype/verify/${verificationId}`, {
      method: 'POST',
      body: JSON.stringify({ confirmed }),
    });

    if (confirmed) {
      showToast('✅ ยืนยันแล้ว! กำลังส่งงานให้ PM...', 'success');
    } else {
      showToast('❌ ยกเลิกคำสั่งแล้ว', 'warning');
    }

    // Refresh verifications
    await loadVerifications();
  } catch (e) {
    showToast(`เกิดข้อผิดพลาด: ${e.message}`, 'error');
  }
}

// ─── Simulator ────────────────────────────────────────────
async function simulateMessage() {
  const text = document.getElementById('simulate-text').value.trim();
  if (!text) {
    showToast('กรุณาพิมพ์คำสั่งก่อน', 'warning');
    return;
  }

  const btn = document.getElementById('btn-simulate');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinning">⏳</span> กำลังประมวลผล...';

  const resultEl = document.getElementById('simulate-result');
  resultEl.style.display = 'none';

  try {
    const result = await apiFetch('/api/skype/simulate', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });

    resultEl.style.display = 'block';
    resultEl.innerHTML = `<strong>ผลลัพธ์:</strong>\n${JSON.stringify(result, null, 2)}`;

    if (result.simulated) {
      showToast('ส่งคำสั่งจำลองสำเร็จ', 'success');
      // รีเฟรช verifications หลัง 1 วินาที
      setTimeout(loadVerifications, 1000);
    }
  } catch (e) {
    resultEl.style.display = 'block';
    resultEl.innerHTML = `<span style="color:var(--color-error)">เกิดข้อผิดพลาด: ${e.message}</span>`;
    showToast(`เกิดข้อผิดพลาด: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '📨 ส่งคำสั่งจำลอง';
  }
}

// ─── Webhook URL ──────────────────────────────────────────
function setWebhookUrl() {
  const urlEl = document.getElementById('webhook-url-display');
  if (urlEl) {
    const baseUrl = window.location.origin.replace('frontend', 'backend') || 'http://localhost:8000';
    // ใช้ URL backend จริง
    urlEl.textContent = `http://YOUR_SERVER_IP:8000/api/skype/webhook`;
  }
}

function copyWebhookUrl() {
  const url = document.getElementById('webhook-url-display')?.textContent || '';
  navigator.clipboard.writeText(url).then(() => {
    showToast('คัดลอก Webhook URL สำเร็จ', 'success');
  }).catch(() => {
    showToast('คัดลอกไม่สำเร็จ กรุณาคัดลอกเอง', 'warning');
  });
}

// ─── Helpers ──────────────────────────────────────────────
function statusColor(status) {
  const colors = {
    pending: 'var(--color-text-muted)',
    awaiting_owner: 'var(--color-warning)',
    confirmed: 'var(--color-success)',
    rejected: 'var(--color-error)',
    forwarded: 'var(--color-info)',
  };
  return colors[status] || 'var(--color-text-muted)';
}

function statusLabel(status) {
  const labels = {
    pending: '⏳ รอดำเนินการ',
    awaiting_owner: '⏰ รอยืนยันจาก Owner',
    confirmed: '✅ ยืนยันแล้ว',
    rejected: '❌ ยกเลิกแล้ว',
    forwarded: '📨 ส่งต่อแล้ว',
  };
  return labels[status] || status;
}
