/* ═══════════════════════════════════════
   logs.js — Central Log Viewer
   ═══════════════════════════════════════ */

// ─── Load Logs ────────────────────────────────────────────
async function loadLogs() {
  const tbody = document.getElementById('logs-tbody');
  tbody.innerHTML = '<tr><td colspan="4" class="loading-text"><span class="spinning">⏳</span> กำลังโหลด...</td></tr>';

  const agentId = document.getElementById('log-filter-agent')?.value || '';
  const level = document.getElementById('log-filter-level')?.value || '';
  const search = document.getElementById('log-search')?.value || '';

  const params = new URLSearchParams({ limit: 200 });
  if (agentId) params.set('agent_id', agentId);
  if (level) params.set('level', level);
  if (search) params.set('search', search);

  try {
    const logs = await apiFetch(`/api/logs?${params}`);
    renderLogsTable(logs);

    const errCount = logs.filter(l => l.level === 'ERROR').length;
    const statsEl = document.getElementById('log-stats');
    if (statsEl) {
      statsEl.innerHTML = `
        ทั้งหมด: <strong>${logs.length}</strong> &nbsp;|&nbsp;
        <span style="color:var(--color-error)">Error: ${errCount}</span> &nbsp;|&nbsp;
        <span style="color:var(--color-success)">Success: ${logs.filter(l=>l.level==='SUCCESS').length}</span>
      `;
    }
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="4" style="color:var(--color-error);padding:2rem;text-align:center">โหลดไม่สำเร็จ: ${e.message}</td></tr>`;
  }
}

function renderLogsTable(logs) {
  const tbody = document.getElementById('logs-tbody');

  if (!logs || !logs.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="loading-text">ไม่มี log ที่ตรงกับเงื่อนไข</td></tr>';
    return;
  }

  tbody.innerHTML = logs.map(l => `
    <tr class="log-row-${l.level}" id="log-${esc(l.id)}">
      <td style="white-space:nowrap;color:var(--color-text-muted);font-size:12px">
        ${formatDate(l.timestamp)}
      </td>
      <td>
        <div style="font-size:13px;font-weight:500">${esc(l.agent_name)}</div>
        <div style="font-size:11px;color:var(--color-text-muted)">${esc(l.agent_id)}</div>
      </td>
      <td>
        <span class="level-badge level-${l.level}">
          ${levelIcon(l.level)} ${l.level}
        </span>
      </td>
      <td style="max-width:500px">
        <div style="font-size:13px">${esc(l.message)}</div>
        ${l.thought_process ? `<div style="font-size:11px;color:var(--color-text-muted);margin-top:4px;white-space:pre-wrap">${esc(l.thought_process.substring(0,200))}</div>` : ''}
      </td>
    </tr>
  `).join('');
}

function prependLogRow(log) {
  const tbody = document.getElementById('logs-tbody');
  if (!tbody) return;

  // ลบ loading text ถ้ามี
  const loadingRow = tbody.querySelector('.loading-text');
  if (loadingRow) loadingRow.parentElement.remove();

  const tr = document.createElement('tr');
  tr.className = `log-row-${log.level}`;
  tr.id = `log-${log.id}`;
  tr.innerHTML = `
    <td style="white-space:nowrap;color:var(--color-text-muted);font-size:12px">
      ${formatDate(log.timestamp)}
    </td>
    <td>
      <div style="font-size:13px;font-weight:500">${esc(log.agent_name)}</div>
      <div style="font-size:11px;color:var(--color-text-muted)">${esc(log.agent_id)}</div>
    </td>
    <td>
      <span class="level-badge level-${log.level}">
        ${levelIcon(log.level)} ${log.level}
      </span>
    </td>
    <td>
      <div style="font-size:13px">${esc(log.message)}</div>
    </td>
  `;
  tbody.prepend(tr);

  // เพิ่ม flash animation สำหรับ ERROR
  if (log.level === 'ERROR') {
    tr.style.animation = 'pulse 0.5s ease 3';
    setTimeout(() => { tr.style.animation = ''; }, 1500);
  }
}

// ─── Filter Events ────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('log-search');
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener('input', () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(loadLogs, 400);
    });
  }

  const levelFilter = document.getElementById('log-filter-level');
  if (levelFilter) levelFilter.addEventListener('change', loadLogs);

  const agentFilter = document.getElementById('log-filter-agent');
  if (agentFilter) agentFilter.addEventListener('change', loadLogs);
});
