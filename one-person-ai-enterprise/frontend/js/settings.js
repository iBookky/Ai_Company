/* ═══════════════════════════════════════
   settings.js — App Settings UI (Verification & Security Hardening)
   ═══════════════════════════════════════ */

// ─── Load Settings ────────────────────────────────────────
async function loadSettings() {
  try {
    const [settings, roomData] = await Promise.all([
      apiFetch('/api/settings'),
      apiFetch('/api/telegram/rooms').catch(() => ({ department_rooms: {} })),
    ]);

    // LLM Keys
    const geminiInput = document.getElementById('gemini-key');
    if (geminiInput) {
      geminiInput.value = settings.gemini_configured ? (settings.gemini_api_key || '••••••••') : '';
    }
    const geminiStatus = document.getElementById('gemini-status');
    if (geminiStatus) {
      geminiStatus.textContent = settings.gemini_configured ? '✅ ตั้งค่าแล้ว' : '❌ ยังไม่ตั้งค่า';
      geminiStatus.className = `config-badge${settings.gemini_configured ? ' ok' : ''}`;
    }

    const claudeInput = document.getElementById('claude-key');
    if (claudeInput) {
      claudeInput.value = settings.anthropic_configured ? (settings.anthropic_api_key || '••••••••') : '';
    }

    // Telegram Bot Token (Main Secretary Bot)
    const tgInput = document.getElementById('telegram-bot-token');
    if (tgInput) {
      tgInput.value = settings.telegram_configured ? (settings.telegram_bot_token || '••••••••') : '';
    }

    // Direct Chat ID
    const directInput = document.getElementById('telegram-direct-chat');
    if (directInput) directInput.value = settings.telegram_owner_direct_chat_id || '';

    // Render PM Bot Tokens Section (Step 3)
    renderPmBotTokensSection(roomData.department_rooms || {});

    // Default Model
    const modelSelect = document.getElementById('default-model');
    if (modelSelect && settings.default_model) {
      modelSelect.value = settings.default_model;
    }
  } catch (e) {
    console.error('loadSettings error:', e);
  }
}

function renderPmBotTokensSection(departmentRooms) {
  const container = document.getElementById('pm-bot-tokens-container');
  if (!container) return;

  const entries = Object.entries(departmentRooms);
  if (!entries.length) {
    container.innerHTML = `<div style="font-size:12px; color:var(--color-text-muted);">⚠️ ยังไม่มี PM/แผนกในระบบ (สร้างทีมใหม่บนหน้าเว็บเพื่อกำหนด Token ของ PM)</div>`;
    return;
  }

  container.innerHTML = entries.map(([deptId, info]) => {
    const pmName = info.pm_name || `PM ${info.name}`;
    const token = info.bot_token || '';
    const statusText = token ? '✅ เชื่อมต่อแล้ว' : '⚠️ ยังไม่ใส่ Token';
    const statusClass = token ? 'color:var(--color-success)' : 'color:var(--color-warning)';

    return `
      <div class="form-group" style="background:rgba(255,255,255,0.02); border:1px solid var(--color-border); border-radius:8px; padding:0.75rem;">
        <label class="form-label" style="display:flex; justify-content:space-between; align-items:center;">
          <span>🤖 PM Bot Token: <strong>${esc(pmName)}</strong> <code style="font-size:11px; color:var(--brand-400);">(${esc(info.name)})</code></span>
          <span style="font-size:11px; ${statusClass}">${statusText}</span>
        </label>
        <input type="text" class="form-input font-mono pm-bot-token-input" data-dept-id="${esc(deptId)}" data-dept-name="${esc(info.name)}" data-pm-name="${esc(pmName)}"
          value="${esc(token)}" placeholder="8776309955:AAxxx... (ใส่ Telegram Bot Token ของ ${esc(pmName)})" />
      </div>
    `;
  }).join('');
}



    // Webhook URL
    const webhookBox = document.getElementById('webhook-url-display');
    if (webhookBox) {
      webhookBox.textContent = `http://YOUR_SERVER_IP:8000/api/telegram/webhook`;
    }

  } catch (e) {
    showToast(`โหลด Settings ไม่สำเร็จ: ${e.message}`, 'error');
  }
}

// ─── Render Department Ops Rows ───────────────────────────
function renderDepartmentOpsRows(departmentRooms, savedOpsChatIds) {
  const container = document.getElementById('dept-ops-container');
  if (!container) return;

  container.innerHTML = '';

  const entries = Object.entries(departmentRooms);

  if (!entries.length) {
    container.innerHTML = `
      <div style="padding:1.2rem; text-align:center; color:var(--color-text-muted); background:rgba(255,255,255,0.02); border-radius:8px; border:1px dashed var(--color-border);">
        <span>🏢 ยังไม่มีแผนกในระบบ — กดปุ่ม <strong>＋ เพิ่มแผนก</strong> ด้านบนเพื่อสร้างแผนกและห้องทำงาน</span>
      </div>`;
    return;
  }

  entries.forEach(([deptId, info]) => {
    const chatVal = info.ops_chat_id || savedOpsChatIds[deptId] || '';

    const row = document.createElement('div');
    row.className = 'dept-ops-row';
    row.style.cssText = 'display:flex; gap:0.5rem; align-items:center; background:rgba(255,255,255,0.03); padding:0.6rem 0.8rem; border-radius:8px; border:1px solid var(--color-border);';
    row.innerHTML = `
      <div style="flex:1.2; font-size:13px; font-weight:500; display:flex; align-items:center; gap:6px;">
        <span>🏢 ${esc(info.name || deptId)}</span>
        <code style="font-size:11px; color:var(--color-text-muted);">(${esc(deptId)})</code>
      </div>
      <div style="flex:1.8; display:flex; gap:6px;">
        <input type="text" class="form-input font-mono dept-ops-input"
          id="dept-input-${esc(deptId)}"
          data-dept-id="${esc(deptId)}"
          value="${esc(chatVal)}"
          placeholder="-100xxxxxxxxx (Chat ID ของแผนกนี้)"
          style="padding:6px 10px; font-size:12px; flex:1;" />
        <button type="button" class="btn btn-sm btn-secondary" onclick="testSendTelegramMessage('dept-input-${esc(deptId)}', 'แผนก ${esc(info.name)}')" title="ทดสอบยิงข้อความจริง">
          📨
        </button>
        <button type="button" class="btn btn-sm btn-danger" onclick="removeDepartmentFromSettings('${esc(deptId)}', '${esc(info.name)}')" title="ยุบแผนก / ลบโฟลเดอร์">
          🗑️
        </button>
      </div>
    `;
    container.appendChild(row);
  });
}

// ─── Add New Department From Settings ──────────────────────
async function addDepartmentOpsRow() {
  const name = prompt('กรอกชื่อแผนกใหม่ที่ต้องการสร้าง (เช่น บัญชี, การตลาด, ทีมขาย, HR):');
  if (!name || !name.trim()) return;

  const chatId = prompt(`กรอก Telegram Ops Chat ID สำหรับแผนก "${name.trim()}" (เว้นว่างไว้ใส่ทีหลังได้):`) || '';

  try {
    await apiFetch('/api/telegram/rooms', {
      method: 'POST',
      body: JSON.stringify({ name: name.trim(), chat_id: chatId.trim() }),
    });

    showToast(`✅ สร้างแผนกและห้องทำงาน "${name.trim()}" เรียบร้อย`, 'success');
    await loadSettings();
  } catch (e) {
    showToast(`สร้างแผนกไม่สำเร็จ: ${e.message}`, 'error');
  }
}

// ─── Dissolve Department From Settings ─────────────────────
async function removeDepartmentFromSettings(deptId, deptName) {
  if (!confirm(`⚠️ ยืนยันการยุบแผนก "${deptName}" (${deptId})?\n\nโฟลเดอร์และไฟล์คอนฟิกทั้งหมดของแผนกนี้จะถูกลบออก`)) {
    return;
  }

  try {
    await apiFetch(`/api/telegram/rooms/${deptId}`, { method: 'DELETE' });
    showToast(`🗑️ ยุบแผนก "${deptName}" เรียบร้อย`, 'success');
    await loadSettings();
  } catch (e) {
    showToast(`ยุบแผนกไม่สำเร็จ: ${e.message}`, 'error');
  }
}

// ─── Save Settings ────────────────────────────────────────
async function saveSettings() {
  const btn = document.getElementById('btn-save-settings');
  const statusEl = document.getElementById('save-status');

  btn.disabled = true;
  btn.innerHTML = '<span class="spinning">⏳</span> กำลังบันทึก...';
  if (statusEl) statusEl.textContent = '';

  const payload = {};

  // LLM Keys
  const geminiKey = document.getElementById('gemini-key')?.value.trim();
  if (geminiKey && !geminiKey.startsWith('••••••••')) {
    payload.gemini_api_key = geminiKey;
  }

  const claudeKey = document.getElementById('claude-key')?.value.trim();
  if (claudeKey && !claudeKey.startsWith('••••••••')) {
    payload.anthropic_api_key = claudeKey;
  }

  // Telegram Bot Token
  const tgToken = document.getElementById('telegram-bot-token')?.value.trim();
  if (tgToken && !tgToken.startsWith('••••••••')) {
    payload.telegram_bot_token = tgToken;
  }

  const directChat = document.getElementById('telegram-direct-chat')?.value.trim();
  if (directChat !== undefined) payload.telegram_owner_direct_chat_id = directChat;

  // Default Model
  const model = document.getElementById('default-model')?.value;
  if (model) payload.default_model = model;

  try {
    const updated = await apiFetch('/api/settings', {
      method: 'PUT',
      body: JSON.stringify(payload),
    });

    // Save PM Bot Tokens
    const pmInputs = document.querySelectorAll('.pm-bot-token-input');
    for (const input of pmInputs) {
      const deptId = input.getAttribute('data-dept-id');
      const deptName = input.getAttribute('data-dept-name');
      const pmName = input.getAttribute('data-pm-name');
      const token = input.value.trim();
      if (deptId && deptName) {
        await apiFetch('/api/telegram/rooms', {
          method: 'POST',
          body: JSON.stringify({ id: deptId, name: deptName, pm_name: pmName, bot_token: token })
        }).catch(err => console.error(`Error saving PM bot token for ${deptId}:`, err));
      }
    }

    showToast('✅ บันทึกการตั้งค่าเรียบร้อย', 'success');
    await loadSettings();
  } catch (e) {
    showToast('บันทึกการตั้งค่าไม่สำเร็จ: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '💾 บันทึกการตั้งค่า';
  }
}





// ─── Test Connection Credentials Live ──────────────────────
async function testSettingsConnection() {
  const btn = document.getElementById('btn-test-settings');
  const box = document.getElementById('test-results-box');

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinning">⏳</span> กำลังทดสอบเชื่อมต่อ...';
  }

  if (box) {
    box.style.display = 'block';
    box.innerHTML = '<div style="color:var(--color-text-muted)">⏳ กำลังเชื่อมต่อสอบถาม Telegram API และ LLM Services...</div>';
  }

  try {
    const res = await apiFetch('/api/settings/test', { method: 'POST' });
    const r = res.results || {};

    let html = '<div style="display:flex; flex-direction:column; gap:8px;">';

    if (r.telegram) {
      html += `
        <div style="padding:8px 12px; border-radius:6px; background:${r.telegram.ok ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}; border:1px solid ${r.telegram.ok ? 'var(--color-success)' : 'var(--color-error)'}; font-weight:500;">
          ${r.telegram.ok ? '✅' : '❌'} Telegram Bot: ${esc(r.telegram.message)}
        </div>`;
    }

    if (r.gemini) {
      html += `
        <div style="padding:8px 12px; border-radius:6px; background:${r.gemini.ok ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}; border:1px solid ${r.gemini.ok ? 'var(--color-success)' : 'var(--color-error)'}; font-weight:500;">
          ${r.gemini.ok ? '✅' : '❌'} Google Gemini API: ${esc(r.gemini.message)}
        </div>`;
    }

    if (r.anthropic) {
      html += `
        <div style="padding:8px 12px; border-radius:6px; background:${r.anthropic.ok ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}; border:1px solid ${r.anthropic.ok ? 'var(--color-success)' : 'var(--color-error)'}; font-weight:500;">
          ${r.anthropic.ok ? '✅' : '❌'} Anthropic Claude API: ${esc(r.anthropic.message)}
        </div>`;
    }

    html += '</div>';

    if (box) box.innerHTML = html;

  } catch (e) {
    if (box) {
      box.innerHTML = `<div style="color:var(--color-error)">❌ ทดสอบเชื่อมต่อไม่สำเร็จ: ${esc(e.message)}</div>`;
    }
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '🧪 ทดสอบการเชื่อมต่อ Token &amp; Keys';
    }
  }
}

// ─── Test Sending Real Message to Specific Telegram Chat ─────
async function testSendTelegramMessage(inputId, labelName) {
  const el = document.getElementById(inputId);
  const chatId = el ? el.value.trim() : '';

  if (!chatId) {
    showToast(`กรุณากรอก Chat ID สำหรับ "${labelName}" ก่อนกดยิงทดสอบ`, 'warning');
    if (el) el.focus();
    return;
  }

  showToast(`⏳ กำลังทดสอบส่งข้อความไปยัง "${labelName}" (${chatId})...`, 'info');

  try {
    const res = await apiFetch('/api/settings/test-message', {
      method: 'POST',
      body: JSON.stringify({
        chat_id: chatId,
        message: `<b>[ทดสอบระบบ — ${labelName}]</b> 🚀 บอท Engfa(GrandTH) เชื่อมต่อสำเร็จเรียบร้อยแล้ว!`
      })
    });

    showToast(`✅ ${res.message}`, 'success');
  } catch (e) {
    showToast(`❌ ส่งทดสอบไม่สำเร็จ: ${e.message}`, 'error');
  }
}
