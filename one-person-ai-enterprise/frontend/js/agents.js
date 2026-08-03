/* ═══════════════════════════════════════
   agents.js — Agent Builder & Management
   ═══════════════════════════════════════ */

let allAgents = [];
let editingAgentId = null;
let _pendingUploadFile = null;
let _pendingUploadCat = null;

// ─── Load Agents Page ─────────────────────────────────────
async function loadAgents() {
  const grid = document.getElementById('agents-grid');
  grid.innerHTML = '<div class="loading-skeleton card"></div><div class="loading-skeleton card"></div>';

  try {
    allAgents = await apiFetch('/api/agents');
    renderAgentsGrid(allAgents);
    populateParentSelect(allAgents);
    document.getElementById('agents-count').textContent = allAgents.length;

    // Update log filter dropdown
    const agentFilter = document.getElementById('log-filter-agent');
    if (agentFilter) {
      agentFilter.innerHTML = '<option value="">ทุก Agent</option>' +
        allAgents.map(a => `<option value="${esc(a.id)}">${esc(a.name)}</option>`).join('');
    }
  } catch (e) {
    grid.innerHTML = `<div class="card" style="padding:2rem;color:var(--color-error)">โหลด Agent ไม่สำเร็จ: ${e.message}</div>`;
  }
}

function renderAgentsGrid(agents) {
  const grid = document.getElementById('agents-grid');

  if (!agents || !agents.length) {
    grid.innerHTML = `
      <div style="grid-column:1/-1">
        <div class="empty-state" style="min-height:300px">
          <span>🤖</span>
          <p>ยังไม่มี Agent</p>
          <button class="btn btn-primary" onclick="openAgentModal()">＋ สร้าง Agent แรก</button>
        </div>
      </div>`;
    return;
  }

  grid.innerHTML = agents.map(agent => {
    const isGoogle = agent.model.startsWith('gemini');
    const modelClass = isGoogle ? 'google' : 'anthropic';
    const modelIcon = isGoogle ? '🔵' : '🟠';
    const tempPct = Math.round(agent.temperature * 100);

    return `
    <div class="agent-card" id="agent-card-${esc(agent.id)}">
      <div class="agent-card-header">
        <div class="agent-avatar">${agentEmoji(agent.role)}</div>
        <div class="agent-meta">
          <div class="agent-name">${esc(agent.name)}</div>
          <div class="agent-dept">${esc(agent.department)}</div>
        </div>
        <div class="agent-card-actions">
          <button class="icon-btn" onclick="openAgentModal('${esc(agent.id)}')" title="แก้ไข">✏️</button>
          <button class="icon-btn danger" onclick="deleteAgent('${esc(agent.id)}', '${esc(agent.name)}')" title="ลบ">🗑️</button>
        </div>
      </div>

      <div class="model-badge ${modelClass}">
        ${modelIcon} ${esc(agent.model)}
      </div>

      <div class="agent-preview">${esc(agent.identity_preview) || 'ยังไม่มี Identity'}</div>

      <div class="agent-footer">
        <div class="temp-indicator">
          <span>🌡️</span>
          <div class="temp-bar">
            <div class="temp-fill" style="width:${tempPct}%"></div>
          </div>
          <span>${agent.temperature}</span>
        </div>
        <div style="display:flex;gap:6px">
          ${agent.has_identity ? '<span title="มี Identity" style="font-size:16px">✅</span>' : '<span title="ไม่มี Identity" style="font-size:16px;opacity:0.4">✅</span>'}
          ${agent.has_skill ? '<span title="มี Skill" style="font-size:16px">🛠️</span>' : '<span title="ไม่มี Skill" style="font-size:16px;opacity:0.4">🛠️</span>'}
        </div>
      </div>
    </div>`;
  }).join('');
}

// ─── Agent Modal ──────────────────────────────────────────
async function openAgentModal(agentId = null) {
  editingAgentId = agentId;
  const modal = document.getElementById('agent-modal');
  const form = document.getElementById('agent-form');
  form.reset();
  document.getElementById('temp-display').textContent = '0.5';

  if (agentId) {
    document.getElementById('modal-title').textContent = '✏️ แก้ไข Agent';
    document.getElementById('btn-submit-agent').textContent = '💾 บันทึกการเปลี่ยนแปลง';

    try {
      const agent = await apiFetch(`/api/agents/${agentId}`);
      document.getElementById('agent-name').value = agent.name || '';
      document.getElementById('agent-model').value = agent.model || 'gemini-1.5-flash';
      document.getElementById('agent-temperature').value = agent.temperature || 0.5;
      document.getElementById('temp-display').textContent = agent.temperature || '0.5';
      const opsInput = document.getElementById('agent-ops-chat');
      if (opsInput) opsInput.value = agent.ops_chat_id || '';
      document.getElementById('agent-identity').value = agent.identity || '';
      document.getElementById('agent-skill').value = agent.skill || '';
    } catch (e) {
      showToast('โหลดข้อมูล Agent ไม่สำเร็จ', 'error');
    }
  } else {
    document.getElementById('modal-title').textContent = '🤖 สร้าง Agent ใหม่';
    document.getElementById('btn-submit-agent').textContent = '💾 บันทึก Agent';
    const opsInput = document.getElementById('agent-ops-chat');
    if (opsInput) opsInput.value = '';
  }

  modal.classList.add('open');
}

function closeAgentModal() {
  document.getElementById('agent-modal').classList.remove('open');
  editingAgentId = null;
}

function populateParentSelect(agents) {
  const select = document.getElementById('agent-parent');
  select.innerHTML = '<option value="">— ไม่มี (ระดับสูงสุด) —</option>' +
    agents.map(a => `<option value="${esc(a.id)}">${esc(a.name)} (${esc(a.department)})</option>`).join('');
}

// ─── Submit Agent Form ────────────────────────────────────
async function submitAgentForm(event) {
  event.preventDefault();
  const btn = document.getElementById('btn-submit-agent');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinning">⏳</span> กำลังบันทึก...';

  const opsInput = document.getElementById('agent-ops-chat');
  const opsChatId = opsInput ? opsInput.value.trim() : '';

  const data = {
    name: document.getElementById('agent-name').value.trim(),
    department: document.getElementById('agent-name').value.trim(),
    parent_department: document.getElementById('agent-parent').value || null,
    model: document.getElementById('agent-model').value,
    temperature: parseFloat(document.getElementById('agent-temperature').value),
    identity: document.getElementById('agent-identity').value.trim(),
    skill: document.getElementById('agent-skill').value.trim(),
    ops_chat_id: opsChatId,
  };

  try {
    if (editingAgentId) {
      await apiFetch(`/api/agents/${editingAgentId}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: data.name,
          model: data.model,
          temperature: data.temperature,
          identity: data.identity,
          skill: data.skill,
          ops_chat_id: data.ops_chat_id,
        }),
      });

      showToast(`อัปเดต "${data.name}" สำเร็จ`, 'success');
    } else {
      await apiFetch('/api/agents', { method: 'POST', body: JSON.stringify(data) });
      showToast(`สร้าง "${data.name}" สำเร็จ! 🎉`, 'success');
    }
    closeAgentModal();
    await loadAgents();
  } catch (e) {
    showToast(`เกิดข้อผิดพลาด: ${e.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = editingAgentId ? '💾 บันทึกการเปลี่ยนแปลง' : '💾 บันทึก Agent';
  }
}

// ─── Delete Agent ─────────────────────────────────────────
async function deleteAgent(agentId, agentName) {
  if (!confirm(`ต้องการลบ "${agentName}" ใช่ไหม?\n\nการกระทำนี้ไม่สามารถย้อนกลับได้`)) return;
  try {
    await apiFetch(`/api/agents/${agentId}`, { method: 'DELETE' });
    showToast(`ลบ "${agentName}" สำเร็จ`, 'warning');
    await loadAgents();
  } catch (e) {
    showToast(`ลบไม่สำเร็จ: ${e.message}`, 'error');
  }
}
