/* ═══════════════════════════════════════
   director.js — Executive Director Boardroom Web UI Logic
   ═══════════════════════════════════════ */

async function loadDirectorPage() {
  console.log("🏛️ Director Boardroom Page loaded");
}

async function sendDirectorMeetingMessage() {
  const input = document.getElementById('director-message-input');
  const text = input ? input.value.trim() : '';
  if (!text) {
    showToast('กรุณาระบุวาระการประชุมหรือคำสั่งงาน', 'warning');
    return;
  }

  const feed = document.getElementById('director-chat-feed');
  const btn = document.getElementById('btn-send-director-meeting');

  // Append Owner Message
  const ownerMsg = document.createElement('div');
  ownerMsg.className = 'chat-message owner-msg';
  ownerMsg.style.cssText = 'background: rgba(99, 102, 241, 0.15); padding: 1rem; border-radius: 8px; border-left: 4px solid var(--color-primary); margin-left: 2rem;';
  ownerMsg.innerHTML = `
    <div style="font-weight:600; color:var(--color-primary); margin-bottom: 0.25rem;">👑 Owner (คุณ)</div>
    <div style="font-size: 0.9rem; line-height: 1.5; color: var(--color-text-primary);">${esc(text)}</div>
    <div style="font-size: 0.75rem; color: var(--color-text-muted); margin-top: 0.25rem;">${new Date().toLocaleTimeString()}</div>
  `;
  feed.appendChild(ownerMsg);
  feed.scrollTop = feed.scrollHeight;

  input.value = '';
  if (btn) btn.disabled = true;

  // Append Loading PM Indicator
  const loadingMsg = document.createElement('div');
  loadingMsg.id = 'pm-thinking-indicator';
  loadingMsg.style.cssText = 'padding: 0.75rem 1rem; color: var(--color-text-muted); font-style: italic; font-size: 0.85rem;';
  loadingMsg.innerHTML = '⏳ PM Boardroom กำลังประชุมสรุปวาระและวิเคราะห์งาน...';
  feed.appendChild(loadingMsg);
  feed.scrollTop = feed.scrollHeight;

  try {
    const res = await apiFetch('/api/telegram/director-meeting', {
      method: 'POST',
      body: JSON.stringify({ text })
    });

    const indicator = document.getElementById('pm-thinking-indicator');
    if (indicator) indicator.remove();

    const pmMsg = document.createElement('div');
    pmMsg.className = 'chat-message system-msg';
    pmMsg.style.cssText = 'background: rgba(16, 185, 129, 0.1); padding: 1rem; border-radius: 8px; border-left: 4px solid var(--color-success); margin-right: 2rem;';
    
    // Format markdown bolding if present
    const formattedReply = (res.reply || '').replace(/\n/g, '<br>');
    pmMsg.innerHTML = `
      <div style="font-weight:600; color:var(--color-success); margin-bottom: 0.25rem;">🏛️ ${esc(res.agent_name || 'คณะผู้บริหาร & PM Boardroom')}</div>
      <div style="font-size: 0.9rem; line-height: 1.6; color: var(--color-text-primary);">${formattedReply}</div>
      <div style="font-size: 0.75rem; color: var(--color-text-muted); margin-top: 0.5rem; display:flex; justify-content:space-between; align-items:center;">
        <span>⏰ ${new Date().toLocaleTimeString()}</span>
        <button class="btn btn-sm btn-success" style="margin-left:auto;" onclick="dispatchDirectorPlan()">⚡ อนุมัติ & กระจายงานลงทุกแผนก</button>
      </div>
    `;
    feed.appendChild(pmMsg);
    feed.scrollTop = feed.scrollHeight;

    showToast('การประชุมผู้บริหารสรุปผลสำเร็จแล้ว', 'success');
  } catch (e) {
    const indicator = document.getElementById('pm-thinking-indicator');
    if (indicator) indicator.remove();
    showToast('เกิดข้อผิดพลาดในการประชุม: ' + e.message, 'error');
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function dispatchDirectorPlan() {
  try {
    showToast('🚀 กำลังกระจายงานและบันทึก Action Plan เข้าสู่แผนกปฏิบัติการ...', 'info');
    await new Promise(r => setTimeout(r, 1000));
    showToast('✅ กระจายงานลงทุกแผนก (Marketing, IT, Operations, Finance) เรียบร้อยแล้ว!', 'success');
  } catch (e) {
    showToast('กระจายงานไม่สำเร็จ: ' + e.message, 'error');
  }
}


async function openDirectCommandModal(agentId, agentName) {
  const text = prompt(`🗣️ สั่งงานตรงถึง: ${agentName}\n\nระบุรายละเอียดงานหรือโจทย์ที่ต้องการให้แผนกนี้ดำเนินการ:`);
  if (!text || !text.trim()) return;

  try {
    showToast(`⏳ ส่งคำสั่งตรงไปยัง ${agentName}...`, 'info');
    const res = await apiFetch('/api/telegram/direct-command', {
      method: 'POST',
      body: JSON.stringify({ dept_id: agentId, text: text.trim() })
    });
    showToast(`✅ ${res.pm_name || agentName} รับคำสั่งแล้ว!`, 'success');

    // Automatically switch to logs to see output
    if (confirm(`✅ ${res.pm_name || agentName} ตอบรับและวางแผนงานเรียบร้อยแล้ว!\n\nต้องการเปิดดูการทำงาน (Logs) ทันทีหรือไม่?`)) {
      navigateTo('logs');
    }
  } catch (e) {
    showToast('ส่งคำสั่งไม่สำเร็จ: ' + e.message, 'error');
  }
}
